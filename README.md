# WType

WType is a keyboard-first Markdown writing app for Windows, macOS, and Linux. It
uses Python and PySide6 for a native desktop interface, visually edits Markdown,
supports fast formatting shortcuts and input rules, keeps crash-recovery drafts,
and exports searchable PDFs.

## Features

- Rich Markdown editing with headings, inline styles, links, lists, quotes, code,
  horizontal rules, and GitHub-flavored Markdown tables.
- `Ctrl+B`/`Cmd+B` for bold, `Ctrl+I`/`Cmd+I` for italic,
  `Ctrl+1`…`Ctrl+6`/`Cmd+1`…`Cmd+6` for headings, and `Ctrl+T`/`Cmd+T` for a table.
- Markdown input rules such as `## `, `- `, `> `, and triple backticks.
- Safe local-file writes, external-change detection, and recovery drafts.
- Automatic left-to-right/right-to-left paragraph layout for English and
  Persian/Arabic writing.
- Direct A4 PDF export with selectable text.
- Distinct, readable typography for all six Markdown heading levels.
- Bundled Outfit typography for Latin text and Vazirmatn typography for
  Persian and Arabic across the interface, writing canvas, and PDF export.
- System, WType Light/Dark, Tokyo Night, Catppuccin, Everforest, Nord,
  Gruvbox, Equilibrium, Solarized, and Adapta themes.
- Adjustable background opacity and optional native blur using Windows Desktop
  Acrylic/DWM or the Wayland `ext-background-effect-v1` protocol supported by Niri.
- Cascadia Mono code typography with subtle, theme-aware translucent gray
  backgrounds for inline code and fenced code blocks.

Opacity and blur are available under **View**. On Windows, WType requests Desktop
Acrylic on current Windows 11 versions and uses composition blur as a fallback on
compatible Windows 10 versions. On Wayland, blur works when the compositor advertises
`ext-background-effect-v1`. On unsupported systems the setting is safely ignored.
Lower the background opacity to make the effect visible.

## Download

Download the archive for your platform from the repository's **Releases** page:

| Platform | Release archive | Run |
|---|---|---|
| Windows (x86-64) | `WType-<version>-windows-x86_64.zip` | Extract and open `WType.exe` |
| macOS (Apple silicon) | `WType-<version>-macos-arm64.zip` | Extract and move `WType.app` to Applications |
| macOS (Intel) | `WType-<version>-macos-x86_64.zip` | Extract and move `WType.app` to Applications |
| Linux (x86-64) | `WType-<version>-linux-x86_64.tar.gz` | Extract and run `./WType` |

The downloadable applications are not currently code-signed. Windows and macOS
may therefore show a security confirmation the first time WType is opened. Each
release includes `SHA256SUMS.txt` so downloads can be verified.

## Run from source

Python 3.11 or newer is required.

```bash
python -m venv .venv
. .venv/bin/activate             # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
wtype
```

You can also open a file directly:

```bash
wtype notes.md
```

On Windows, the same setup can be run from PowerShell without activating the
virtual environment:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\wtype.exe
```

## Keyboard shortcuts

“Primary” is Ctrl on Windows/Linux and Cmd on macOS.

| Action | Shortcut |
|---|---|
| Bold / Italic | Primary+B / Primary+I |
| Strikethrough | Primary+Shift+X |
| Inline code / Link | Primary+E / Primary+K |
| Paragraph / Heading 1–6 | Primary+0 / Primary+1…6 |
| Table | Primary+T |
| Bullet / numbered list | Primary+Shift+8 / Primary+Shift+7 |
| Blockquote / code block | Primary+Shift+Q / Primary+Shift+C |
| Horizontal rule | Primary+Shift+H |
| Export PDF | Primary+Shift+E |
| Shortcut reference | Primary+/ |

## Quality checks

```bash
pytest
ruff check .
mypy
```

For headless Linux test environments, set `QT_QPA_PLATFORM=offscreen`.

## Packaging and releasing

Qt's deployment tool builds the application for the current platform:

```bash
python -c "from pathlib import Path; Path('dist').mkdir(exist_ok=True)"
pyside6-deploy -c pysidedeploy.spec --force
```

GitHub Actions builds all supported release archives when a version tag is
pushed. The tag must match the version in `pyproject.toml`:

```bash
git tag v0.1.1
git push origin v0.1.1
```

The release can also be started from **Actions → Release → Run workflow** with a
matching tag. The workflow runs the quality checks, builds each native
application on its target operating system, creates checksums, and publishes the
GitHub Release automatically.

## License

Copyright © 2026 WType contributors.

WType is free software distributed under the GNU General Public License,
version 3 only. See [LICENSE](LICENSE) for the full terms.

The bundled Outfit font is copyright © 2021 The Outfit Project Authors and is
distributed under the SIL Open Font License 1.1. See
`src/wtype/assets/OFL-Outfit.txt` in the source tree or `OUTFIT-LICENSE.txt` in
a release archive for its terms.

The bundled Vazirmatn font is copyright © 2015 The Vazirmatn Project Authors
and is distributed under the SIL Open Font License 1.1. See
`src/wtype/assets/OFL-Vazirmatn.txt` in the source tree or
`VAZIRMATN-LICENSE.txt` in a release archive for its terms.

The bundled Cascadia Mono font is copyright © Microsoft Corporation and is
distributed under the SIL Open Font License 1.1. See
`src/wtype/assets/OFL-Cascadia.txt` in the source tree or
`CASCADIA-MONO-LICENSE.txt` in a release archive for its terms.
