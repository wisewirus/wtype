[app]

# Application name and project layout.
title = WType
project_dir = .
input_file = src/wtype/__main__.py
exec_directory = dist
project_file =
icon =

[python]

# pyside6-deploy uses the active interpreter; this value keeps the config portable.
python_path = python
packages = Nuitka==4.1.1
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]

# Empty values are detected per platform when the deployment command runs.
qml_files =
excluded_qml_plugins =
modules =
plugins =

[android]

wheel_pyside =
wheel_shiboken =
plugins =

[nuitka]

macos.permissions =
mode = onefile
extra_args = --quiet --noinclude-qt-translations --assume-yes-for-downloads

[buildozer]

mode = debug
recipe_dir =
jars_dir =
ndk_path =
sdk_path =
local_libs =
arch =
