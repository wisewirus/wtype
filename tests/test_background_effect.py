import ctypes
from collections.abc import Callable
from typing import Any

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QWidget

from wtype.background_effect import (
    BackgroundEffect,
    _AccentPolicy,
    _WindowCompositionAttributeData,
    _WindowsBlur,
)


class _FakeFunction:
    def __init__(self, callback: Callable[..., int]) -> None:
        self._callback = callback
        self.argtypes: list[Any] = []
        self.restype: Any = None

    def __call__(self, *args: object) -> int:
        return self._callback(*args)


class _FakeLibrary:
    pass


def _windows_libraries(
    dwm_result: int,
    alpha_result: int | None = None,
) -> tuple[_FakeLibrary, _FakeLibrary, list[int], list[bool], list[int]]:
    backdrop_values: list[int] = []
    alpha_values: list[bool] = []
    accent_values: list[int] = []

    def set_dwm_attribute(
        _handle: object,
        attribute: ctypes.c_uint32,
        value_pointer: object,
        value_size: ctypes.c_uint32,
    ) -> int:
        assert value_size.value == ctypes.sizeof(ctypes.c_int)
        value = ctypes.cast(value_pointer, ctypes.POINTER(ctypes.c_int)).contents
        if attribute.value == 38:
            backdrop_values.append(value.value)
            return dwm_result
        assert attribute.value == 39
        alpha_values.append(bool(value.value))
        return dwm_result if alpha_result is None else alpha_result

    def set_composition_attribute(_handle: object, data_pointer: object) -> int:
        data = ctypes.cast(
            data_pointer, ctypes.POINTER(_WindowCompositionAttributeData)
        ).contents
        assert data.attribute == 19
        assert data.data_size == ctypes.sizeof(_AccentPolicy)
        policy = ctypes.cast(data.data, ctypes.POINTER(_AccentPolicy)).contents
        accent_values.append(policy.accent_state)
        return 1

    dwmapi = _FakeLibrary()
    dwmapi.DwmSetWindowAttribute = _FakeFunction(set_dwm_attribute)  # type: ignore[attr-defined]
    user32 = _FakeLibrary()
    user32.SetWindowCompositionAttribute = _FakeFunction(  # type: ignore[attr-defined]
        set_composition_attribute
    )
    return dwmapi, user32, backdrop_values, alpha_values, accent_values


def test_windows_blur_uses_desktop_acrylic_when_available() -> None:
    dwmapi, user32, backdrop_values, alpha_values, accent_values = _windows_libraries(0)
    effect = _WindowsBlur(123, dwmapi, user32)

    assert effect.connect()
    assert effect.available
    assert effect.set_enabled(True)
    assert effect.set_enabled(False)
    assert backdrop_values == [1, 3, 1]
    assert alpha_values == [True]
    assert accent_values == []

    effect.close()
    assert not effect.available
    assert backdrop_values == [1, 3, 1, 1]
    assert alpha_values == [True, False]


def test_windows_blur_falls_back_to_windows_10_composition_api() -> None:
    dwmapi, user32, backdrop_values, alpha_values, accent_values = _windows_libraries(-1)
    effect = _WindowsBlur(123, dwmapi, user32)

    assert effect.connect()
    assert effect.available
    assert effect.set_enabled(True)
    assert effect.set_enabled(False)
    assert backdrop_values == [1]
    assert alpha_values == []
    assert accent_values == [0, 2, 3, 2]

    effect.close()
    assert not effect.available
    assert accent_values == [0, 2, 3, 2, 0]


def test_windows_blur_falls_back_when_redirection_alpha_is_unavailable() -> None:
    dwmapi, user32, backdrop_values, alpha_values, accent_values = _windows_libraries(
        0, alpha_result=-1
    )
    effect = _WindowsBlur(123, dwmapi, user32)

    assert effect.connect()
    assert effect.available
    assert effect.set_enabled(True)
    assert backdrop_values == [1]
    assert alpha_values == [True]
    assert accent_values == [0, 2, 3]


def test_blur_setting_degrades_safely_without_wayland(qapp) -> None:  # type: ignore[no-untyped-def]
    window = QWidget()
    effect = BackgroundEffect(window)

    assert not effect.initialize()
    assert not effect.set_enabled(True)
    assert effect.enabled
    assert not effect.available
    assert effect.error
