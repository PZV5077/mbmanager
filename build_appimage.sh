#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Build AppImage package for MBManager.

Usage:
  ./build_appimage.sh --version <version> [options]

Required:
  --version <version>       Release version (example: 2.1.0)

Options:
  --app-id <id>             Desktop/AppImage id (default: mbmanager)
  --app-name <name>         Human-readable app name (default: MBManager)
  --bin-name <name>         Executable name in package (default: mbmanager)
  --entrypoint <path>       Python entrypoint (default: main.py)
  --python <path>           Python executable (default: python3)
  --requirements <path>     Requirements file (default: requirements.txt)
  --icon-svg <path>         SVG icon path (default: icon/icon.svg)
  --output-dir <path>       Output directory for AppImage (default: dist)
  --build-dir <path>        Temporary build directory (default: .build/appimage)
  --clean                   Remove prior build dir for this version first
  -h, --help                Show this help

Notes:
  - This script only prepares and builds AppImage when run.
  - It is release-friendly: versioned output filename and isolated build path.
  - By default it uses icon/icon.svg as requested.
EOF
}

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VERSION=""
APP_ID="mbmanager"
APP_NAME="MBManager"
BIN_NAME="mbmanager"
ENTRYPOINT="main.py"
PYTHON_BIN="python3"
REQUIREMENTS_FILE="requirements.txt"
ICON_SVG="icon/icon.svg"
OUTPUT_DIR="dist"
BUILD_DIR=".build/appimage"
DO_CLEAN="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="${2:-}"
      shift 2
      ;;
    --app-id)
      APP_ID="${2:-}"
      shift 2
      ;;
    --app-name)
      APP_NAME="${2:-}"
      shift 2
      ;;
    --bin-name)
      BIN_NAME="${2:-}"
      shift 2
      ;;
    --entrypoint)
      ENTRYPOINT="${2:-}"
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:-}"
      shift 2
      ;;
    --requirements)
      REQUIREMENTS_FILE="${2:-}"
      shift 2
      ;;
    --icon-svg)
      ICON_SVG="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --build-dir)
      BUILD_DIR="${2:-}"
      shift 2
      ;;
    --clean)
      DO_CLEAN="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "Error: --version is required" >&2
  usage
  exit 1
fi

ENTRYPOINT_PATH="$PROJECT_ROOT/$ENTRYPOINT"
REQUIREMENTS_PATH="$PROJECT_ROOT/$REQUIREMENTS_FILE"
ICON_SVG_PATH="$PROJECT_ROOT/$ICON_SVG"
OUT_DIR_PATH="$PROJECT_ROOT/$OUTPUT_DIR"
BUILD_ROOT="$PROJECT_ROOT/$BUILD_DIR/${APP_ID}-${VERSION}"
APPDIR="$BUILD_ROOT/AppDir"
VENV_DIR="$BUILD_ROOT/venv"
PYI_WORK="$BUILD_ROOT/pyinstaller/work"
PYI_SPEC="$BUILD_ROOT/pyinstaller/spec"
PYI_DIST="$BUILD_ROOT/pyinstaller/dist"
ICON_PNG_PATH="$BUILD_ROOT/${APP_ID}.png"

case "$(uname -m)" in
  x86_64|amd64) APPIMAGE_ARCH="x86_64" ;;
  aarch64|arm64) APPIMAGE_ARCH="aarch64" ;;
  *) APPIMAGE_ARCH="$(uname -m)" ;;
esac

OUTPUT_FILE="$OUT_DIR_PATH/${APP_ID}-${VERSION}-${APPIMAGE_ARCH}.AppImage"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "Missing required file: $1" >&2
    exit 1
  fi
}

make_icon_png() {
  if command -v rsvg-convert >/dev/null 2>&1; then
    rsvg-convert -w 256 -h 256 "$ICON_SVG_PATH" -o "$ICON_PNG_PATH"
    return
  fi

  if command -v inkscape >/dev/null 2>&1; then
    inkscape "$ICON_SVG_PATH" --export-type=png --export-filename="$ICON_PNG_PATH" --export-width=256 --export-height=256 >/dev/null 2>&1
    return
  fi

  if command -v magick >/dev/null 2>&1; then
    magick -background none "$ICON_SVG_PATH" -resize 256x256 "$ICON_PNG_PATH"
    return
  fi

  echo "Unable to convert SVG to PNG. Install one of: rsvg-convert, inkscape, or imagemagick (magick)." >&2
  exit 1
}

require_cmd "$PYTHON_BIN"
require_cmd appimagetool
require_file "$ENTRYPOINT_PATH"
require_file "$REQUIREMENTS_PATH"
require_file "$ICON_SVG_PATH"

if [[ "$DO_CLEAN" == "1" && -d "$BUILD_ROOT" ]]; then
  rm -rf "$BUILD_ROOT"
fi

mkdir -p "$OUT_DIR_PATH" "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"

"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r "$REQUIREMENTS_PATH"
python -m pip install pyinstaller

python -m PyInstaller \
  --noconfirm \
  --clean \
  --name "$BIN_NAME" \
  --windowed \
  --onedir \
  --distpath "$PYI_DIST" \
  --workpath "$PYI_WORK" \
  --specpath "$PYI_SPEC" \
  "$ENTRYPOINT_PATH"

cp -a "$PYI_DIST/$BIN_NAME/." "$APPDIR/usr/bin/"

cat > "$APPDIR/AppRun" <<EOF
#!/usr/bin/env bash
set -euo pipefail
HERE="\$(dirname "\$(readlink -f "\${BASH_SOURCE[0]}")")"
exec "\$HERE/usr/bin/$BIN_NAME" "\$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/usr/share/applications/$APP_ID.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=$BIN_NAME
Icon=$APP_ID
Categories=Office;Utility;
Terminal=false
StartupNotify=true
EOF
cp "$APPDIR/usr/share/applications/$APP_ID.desktop" "$APPDIR/$APP_ID.desktop"

make_icon_png
cp "$ICON_PNG_PATH" "$APPDIR/$APP_ID.png"
cp "$ICON_PNG_PATH" "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP_ID.png"

ARCH="$APPIMAGE_ARCH" appimagetool "$APPDIR" "$OUTPUT_FILE"

echo "AppImage created: $OUTPUT_FILE"
