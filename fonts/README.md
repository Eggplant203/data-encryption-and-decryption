# Fonts Directory

This directory contains font files used by the application for rendering custom text in barcode mode.

## Font Priority

When rendering custom text in barcode mode, the application will try to use fonts in the following order:

1. **FiraCode-Regular.ttf** (project local)
2. **FiraCode.ttf** (project local)
3. **firacode-regular.ttf** (project local)
4. **FiraCode-Regular.ttf** (system fonts)
5. **FiraCode.ttf** (system fonts)
6. **Consolas** (Windows system font - excellent fallback)
7. **Courier New** (classic monospace)
8. **DejaVu Sans Mono** (cross-platform)
9. **Arial** (final fallback)
10. **Default PIL font** (last resort)

## Installation

### Automatic Installation

The font FiraCode-Regular.ttf is automatically downloaded and installed in this directory when needed.

### Manual Installation

If you want to install FiraCode manually:

1. Download FiraCode from: https://github.com/tonsky/FiraCode/releases
2. Extract the TTF files
3. Copy `FiraCode-Regular.ttf` to this directory

## Font Features

- **FiraCode**: Modern monospace font with programming ligatures
- **Consolas**: Excellent Windows monospace font, very readable
- **Courier New**: Classic monospace, universally available
- **DejaVu Sans Mono**: Good cross-platform monospace option

## Usage in Code

The font selection logic is implemented in `src/barcode_mode.py` in the `encode()` function. It automatically tries each font in order until one loads successfully.

## Files

- `FiraCode-Regular.ttf` - Primary font for custom text rendering
- `ttf/` - Directory containing full FiraCode font family
- `variable_ttf/` - Variable font versions
- `woff/`, `woff2/` - Web font versions (not used by Python)
