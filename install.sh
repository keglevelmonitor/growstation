#!/bin/bash
# install.sh — GrowStation installer
set -e

echo "=========================================="
echo "    GrowStation Installer"
echo "=========================================="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_EXEC="python3"
VENV_DIR="$PROJECT_DIR/venv"
VENV_PYTHON_EXEC="$VENV_DIR/bin/python"
DATA_DIR="${DATA_DIR:-$HOME/growstation-data}"
DESKTOP_FILENAME="${DESKTOP_FILENAME:-growstation.desktop}"
APP_TITLE="${APP_TITLE:-GrowStation}"
DESKTOP_FILE_TEMPLATE="$PROJECT_DIR/growstation.desktop"
INSTALL_LOCATION="$HOME/.local/share/applications/$DESKTOP_FILENAME"

echo "Project path:   $PROJECT_DIR"
echo "Data directory: $DATA_DIR"
echo "App Title:      $APP_TITLE"

echo ""
echo "--- [Step 1/5] Checking System Dependencies ---"
sudo apt-get update
sudo apt-get install -y python3-dev python3-venv liblgpio-dev numlockx libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev

echo ""
echo "--- [Step 2/5] Setting up Virtual Environment ---"
if [ -d "$VENV_DIR" ]; then
    echo "Removing old venv..."
    rm -rf "$VENV_DIR"
fi
$PYTHON_EXEC -m venv "$VENV_DIR"
[ $? -ne 0 ] && { echo "[FATAL] venv failed."; exit 1; }

echo ""
echo "--- [Step 3/5] Installing Python Libraries ---"
"$VENV_PYTHON_EXEC" -m pip install --upgrade pip
"$VENV_PYTHON_EXEC" -m pip install -r "$PROJECT_DIR/requirements.txt"
[ $? -ne 0 ] && { echo "[FATAL] pip install failed."; exit 1; }

echo ""
echo "--- [Step 4/5] Configuring Data Directory ---"
mkdir -p "$DATA_DIR"
chmod 700 "$DATA_DIR"

echo ""
echo "--- [Step 5/5] Installing Desktop Shortcut ---"
ICON_SOURCE="$PROJECT_DIR/src/assets/growstation.png"
if [ -f "$ICON_SOURCE" ]; then
    sudo cp "$ICON_SOURCE" "/usr/share/icons/growstation.png"
    sudo mkdir -p /usr/share/icons/hicolor/48x48/apps
    sudo cp "$ICON_SOURCE" "/usr/share/icons/hicolor/48x48/apps/growstation.png"
fi

if [ -f "$DESKTOP_FILE_TEMPLATE" ]; then
    EXEC_CMD="$VENV_PYTHON_EXEC $PROJECT_DIR/src/main_kivy.py"
    cp "$DESKTOP_FILE_TEMPLATE" /tmp/growstation_temp.desktop
    sed -i "s|Exec=PLACEHOLDER_EXEC_PATH|Exec=$EXEC_CMD|g" /tmp/growstation_temp.desktop
    sed -i "s|Path=PLACEHOLDER_PATH|Path=$PROJECT_DIR/src|g" /tmp/growstation_temp.desktop
    mkdir -p "$HOME/.local/share/applications"
    mv /tmp/growstation_temp.desktop "$INSTALL_LOCATION"
    chmod +x "$INSTALL_LOCATION"
    echo "Shortcut: $INSTALL_LOCATION"
fi

echo ""
echo "Installation complete!"
echo "Run GrowStation from Applications > Other > $APP_TITLE"
echo ""
