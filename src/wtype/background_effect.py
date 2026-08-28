from __future__ import annotations

import ctypes
import sys
from typing import Any

from PySide6.QtWidgets import QApplication, QWidget


class _AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("accent_state", ctypes.c_int),
        ("accent_flags", ctypes.c_uint32),
        ("gradient_color", ctypes.c_uint32),
        ("animation_id", ctypes.c_uint32),
    ]


class _WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [
        ("attribute", ctypes.c_int),
        ("data", ctypes.c_void_p),
        ("data_size", ctypes.c_uint32),
    ]


class _WindowsBlur:
    """Native Windows backdrop, with a composition blur fallback."""

    _DWMWA_SYSTEMBACKDROP_TYPE = 38
    _DWMSBT_NONE = 1
    _DWMSBT_TRANSIENTWINDOW = 3
    _WCA_ACCENT_POLICY = 19
    _ACCENT_DISABLED = 0
    _ACCENT_ENABLE_BLURBEHIND = 3

    def __init__(
        self,
        window_handle: int,
        dwmapi: Any | None = None,
        user32: Any | None = None,
    ) -> None:
        windows_library = getattr(ctypes, "WinDLL", ctypes.CDLL)
        if dwmapi is None:
            dwmapi = windows_library("dwmapi", use_last_error=True)
        if user32 is None:
            user32 = windows_library("user32", use_last_error=True)

        self._window_handle = window_handle
        self._mode = ""
        self._dwm_set_window_attribute = dwmapi.DwmSetWindowAttribute
        self._dwm_set_window_attribute.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
        ]
        self._dwm_set_window_attribute.restype = ctypes.c_long

        self._set_window_composition_attribute = getattr(
            user32, "SetWindowCompositionAttribute", None
        )
        if self._set_window_composition_attribute is not None:
            self._set_window_composition_attribute.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(_WindowCompositionAttributeData),
            ]
            self._set_window_composition_attribute.restype = ctypes.c_int

    @property
    def available(self) -> bool:
        return bool(self._mode)

    def connect(self) -> bool:
        # Desktop Acrylic through the documented API is available on current
        # Windows 11 releases. Setting NONE is also a side-effect-free probe.
        if self._set_system_backdrop(self._DWMSBT_NONE):
            self._mode = "system_backdrop"
            return True

        # Windows 10 and early Windows 11 builds expose the older composition
        # accent API instead. It has no import library, so it is loaded at run time.
        if self._set_accent(self._ACCENT_DISABLED):
            self._mode = "accent"
            return True
        return False

    def set_enabled(self, enabled: bool) -> bool:
        if self._mode == "system_backdrop":
            backdrop = self._DWMSBT_TRANSIENTWINDOW if enabled else self._DWMSBT_NONE
            return self._set_system_backdrop(backdrop)
        if self._mode == "accent":
            accent = self._ACCENT_ENABLE_BLURBEHIND if enabled else self._ACCENT_DISABLED
            return self._set_accent(accent)
        return False

    def close(self) -> None:
        if self._mode:
            self.set_enabled(False)
            self._mode = ""

    def _set_system_backdrop(self, backdrop: int) -> bool:
        value = ctypes.c_int(backdrop)
        result = self._dwm_set_window_attribute(
            ctypes.c_void_p(self._window_handle),
            ctypes.c_uint32(self._DWMWA_SYSTEMBACKDROP_TYPE),
            ctypes.byref(value),
            ctypes.c_uint32(ctypes.sizeof(value)),
        )
        return bool(result >= 0)

    def _set_accent(self, accent_state: int) -> bool:
        if self._set_window_composition_attribute is None:
            return False
        policy = _AccentPolicy(accent_state, 0, 0, 0)
        data = _WindowCompositionAttributeData(
            self._WCA_ACCENT_POLICY,
            ctypes.addressof(policy),
            ctypes.sizeof(policy),
        )
        return bool(
            self._set_window_composition_attribute(
                ctypes.c_void_p(self._window_handle), ctypes.byref(data)
            )
        )


class _WlMessage(ctypes.Structure):
    pass


class _WlInterface(ctypes.Structure):
    pass


_WlMessage._fields_ = [
    ("name", ctypes.c_char_p),
    ("signature", ctypes.c_char_p),
    ("types", ctypes.c_void_p),
]
_WlInterface._fields_ = [
    ("name", ctypes.c_char_p),
    ("version", ctypes.c_int),
    ("method_count", ctypes.c_int),
    ("methods", ctypes.POINTER(_WlMessage)),
    ("event_count", ctypes.c_int),
    ("events", ctypes.POINTER(_WlMessage)),
]

_REGISTRY_GLOBAL = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.c_char_p,
    ctypes.c_uint32,
)
_REGISTRY_REMOVE = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
)
_CAPABILITIES = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32)


class _RegistryListener(ctypes.Structure):
    _fields_ = [("global_", _REGISTRY_GLOBAL), ("global_remove", _REGISTRY_REMOVE)]


class _ManagerListener(ctypes.Structure):
    _fields_ = [("capabilities", _CAPABILITIES)]


class _ProtocolDefinitions:
    """Keep the protocol metadata alive for the lifetime of its Wayland proxies."""

    def __init__(self, library: ctypes.CDLL) -> None:
        self.registry = _WlInterface.in_dll(library, "wl_registry_interface")
        self.region = _WlInterface.in_dll(library, "wl_region_interface")
        self.surface = _WlInterface.in_dll(library, "wl_surface_interface")

        self.effect_surface = _WlInterface()
        self.types = (ctypes.c_void_p * 4)(
            0,
            ctypes.addressof(self.effect_surface),
            ctypes.addressof(self.surface),
            ctypes.addressof(self.region),
        )
        types_address = ctypes.addressof(self.types)
        pointer_size = ctypes.sizeof(ctypes.c_void_p)

        self.manager_requests = (_WlMessage * 2)(
            _WlMessage(b"destroy", b"", types_address),
            _WlMessage(b"get_background_effect", b"no", types_address + pointer_size),
        )
        self.manager_events = (_WlMessage * 1)(
            _WlMessage(b"capabilities", b"u", types_address),
        )
        self.manager = _WlInterface(
            b"ext_background_effect_manager_v1",
            1,
            2,
            self.manager_requests,
            1,
            self.manager_events,
        )

        self.effect_requests = (_WlMessage * 2)(
            _WlMessage(b"destroy", b"", types_address),
            _WlMessage(b"set_blur_region", b"?o", types_address + 3 * pointer_size),
        )
        self.effect_surface.name = b"ext_background_effect_surface_v1"
        self.effect_surface.version = 1
        self.effect_surface.method_count = 2
        self.effect_surface.methods = self.effect_requests
        self.effect_surface.event_count = 0
        self.effect_surface.events = ctypes.POINTER(_WlMessage)()


class _WaylandBlur:
    _DESTROY = 1
    _BLUR_CAPABILITY = 1

    def __init__(self, display: int, compositor: int, surface: int) -> None:
        self._library = ctypes.CDLL("libwayland-client.so.0")
        self._protocol = _ProtocolDefinitions(self._library)
        self._display = display
        self._compositor = compositor
        self._surface = surface
        self._registry = 0
        self._manager = 0
        self._effect = 0
        self._capabilities = 0

        self._library.wl_proxy_get_version.argtypes = [ctypes.c_void_p]
        self._library.wl_proxy_get_version.restype = ctypes.c_uint32
        self._library.wl_proxy_marshal_flags.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(_WlInterface),
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        self._library.wl_proxy_marshal_flags.restype = ctypes.c_void_p
        self._library.wl_proxy_add_listener.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
        ]
        self._library.wl_proxy_add_listener.restype = ctypes.c_int
        self._library.wl_display_roundtrip.argtypes = [ctypes.c_void_p]
        self._library.wl_display_roundtrip.restype = ctypes.c_int
        self._library.wl_proxy_destroy.argtypes = [ctypes.c_void_p]
        self._library.wl_proxy_destroy.restype = None

        self._global_callback = _REGISTRY_GLOBAL(self._on_global)
        self._remove_callback = _REGISTRY_REMOVE(self._on_global_remove)
        self._capabilities_callback = _CAPABILITIES(self._on_capabilities)
        self._registry_listener = _RegistryListener(
            self._global_callback,
            self._remove_callback,
        )
        self._manager_listener = _ManagerListener(self._capabilities_callback)

    @property
    def available(self) -> bool:
        return bool(self._manager and self._capabilities & self._BLUR_CAPABILITY)

    def connect(self) -> bool:
        display_version = self._version(self._display)
        self._registry = self._marshal(
            self._display,
            1,
            self._protocol.registry,
            display_version,
            0,
            ctypes.c_void_p(),
        )
        if not self._registry:
            return False
        self._add_listener(self._registry, self._registry_listener)
        if self._library.wl_display_roundtrip(self._display) < 0 or not self._manager:
            return False
        if self._library.wl_display_roundtrip(self._display) < 0:
            return False
        return self.available

    def set_enabled(self, enabled: bool) -> bool:
        if not self.available:
            return False
        if not self._effect:
            self._effect = self._marshal(
                self._manager,
                1,
                self._protocol.effect_surface,
                self._version(self._manager),
                0,
                ctypes.c_void_p(),
                ctypes.c_void_p(self._surface),
            )
            if not self._effect:
                return False

        region = 0
        if enabled:
            region = self._marshal(
                self._compositor,
                1,
                self._protocol.region,
                self._version(self._compositor),
                0,
                ctypes.c_void_p(),
            )
            if not region:
                return False
            self._marshal(
                region,
                1,
                None,
                self._version(region),
                0,
                ctypes.c_int32(0),
                ctypes.c_int32(0),
                ctypes.c_int32(2_147_483_647),
                ctypes.c_int32(2_147_483_647),
            )

        self._marshal(
            self._effect,
            1,
            None,
            self._version(self._effect),
            0,
            ctypes.c_void_p(region),
        )
        if region:
            self._marshal(
                region,
                0,
                None,
                self._version(region),
                self._DESTROY,
            )
        self._commit()
        return True

    def close(self) -> None:
        if self._effect:
            self._marshal(
                self._effect,
                0,
                None,
                self._version(self._effect),
                self._DESTROY,
            )
            self._effect = 0
            self._commit()
        if self._manager:
            self._marshal(
                self._manager,
                0,
                None,
                self._version(self._manager),
                self._DESTROY,
            )
            self._manager = 0
        if self._registry:
            self._library.wl_proxy_destroy(self._registry)
            self._registry = 0

    def _commit(self) -> None:
        self._marshal(self._surface, 6, None, self._version(self._surface), 0)

    def _version(self, proxy: int) -> int:
        return int(self._library.wl_proxy_get_version(proxy))

    def _marshal(
        self,
        proxy: int,
        opcode: int,
        interface: _WlInterface | None,
        version: int,
        flags: int,
        *arguments: object,
    ) -> int:
        interface_pointer = (
            ctypes.pointer(interface) if interface is not None else ctypes.POINTER(_WlInterface)()
        )
        result = self._library.wl_proxy_marshal_flags(
            ctypes.c_void_p(proxy),
            ctypes.c_uint32(opcode),
            interface_pointer,
            ctypes.c_uint32(version),
            ctypes.c_uint32(flags),
            *arguments,
        )
        return int(result or 0)

    def _add_listener(self, proxy: int, listener: ctypes.Structure) -> None:
        callbacks = ctypes.cast(ctypes.pointer(listener), ctypes.POINTER(ctypes.c_void_p))
        if self._library.wl_proxy_add_listener(proxy, callbacks, None) != 0:
            raise RuntimeError("Could not add a Wayland protocol listener")

    def _on_global(
        self,
        _data: int,
        registry: int,
        name: int,
        interface: bytes,
        version: int,
    ) -> None:
        if interface != b"ext_background_effect_manager_v1" or self._manager:
            return
        self._manager = self._marshal(
            registry,
            0,
            self._protocol.manager,
            min(version, 1),
            0,
            ctypes.c_uint32(name),
            ctypes.c_char_p(self._protocol.manager.name),
            ctypes.c_uint32(1),
            ctypes.c_void_p(),
        )
        if self._manager:
            self._add_listener(self._manager, self._manager_listener)

    def _on_global_remove(self, _data: int, _registry: int, _name: int) -> None:
        return

    def _on_capabilities(self, _data: int, _manager: int, flags: int) -> None:
        self._capabilities = flags


class BackgroundEffect:
    """Optional native background blur for a top-level Qt window."""

    def __init__(self, window: QWidget) -> None:
        self._window = window
        self._backend: _WaylandBlur | _WindowsBlur | None = None
        self._enabled = False
        self.error = ""

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def available(self) -> bool:
        return self._backend is not None and self._backend.available

    def initialize(self) -> bool:
        if self._backend is not None:
            return self._backend.available
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            self.error = "Background blur requires a running graphical application."
            return False

        if sys.platform == "win32":
            return self._initialize_windows()
        if sys.platform == "linux" and app.platformName().lower() == "wayland":
            return self._initialize_wayland(app)

        self.error = "Background blur is available on Windows and supported Wayland compositors."
        return False

    def _initialize_windows(self) -> bool:
        try:
            window_handle = int(self._window.winId())
            if not window_handle:
                raise RuntimeError("Qt did not expose its native window handle")
            backend = _WindowsBlur(window_handle)
            if not backend.connect():
                backend.close()
                self.error = "This Windows version does not provide a compatible blur effect."
                return False
            self._backend = backend
            if self._enabled:
                backend.set_enabled(True)
            self.error = ""
            return True
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            self.error = f"Windows background blur is unavailable: {exc}"
            return False

    def _initialize_wayland(self, app: QApplication) -> bool:
        try:
            native: Any = app.nativeInterface()
            display = int(native.display())
            compositor = int(native.compositor())
            surface = int(self._window.winId())
            if not display or not compositor or not surface:
                raise RuntimeError("Qt did not expose its Wayland surface")
            backend = _WaylandBlur(display, compositor, surface)
            if not backend.connect():
                backend.close()
                self.error = "The compositor does not advertise ext-background-effect-v1 blur."
                return False
            self._backend = backend
            if self._enabled:
                backend.set_enabled(True)
            self.error = ""
            return True
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            self.error = f"Wayland blur is unavailable: {exc}"
            return False

    def set_enabled(self, enabled: bool) -> bool:
        self._enabled = enabled
        if self._backend is None:
            return False
        return self._backend.set_enabled(enabled)

    def close(self) -> None:
        if self._backend is not None:
            self._backend.close()
            self._backend = None
