# Nuitka builds on Windows should behave like GUI applications, without a console window.
# nuitka-project-if: {OS} == "Windows":
#    nuitka-project: --windows-console-mode=disable

from wtype.app import main

raise SystemExit(main())
