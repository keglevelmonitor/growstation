#!/bin/bash
# update.sh — Handles git pull and dependency updates for GrowStation.

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
VENV_PYTHON_EXEC="$VENV_DIR/bin/python"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

echo "--- GrowStation Update Manager ---"
echo "Root: $PROJECT_DIR"
echo "Branch: $BRANCH"

if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo "[ERROR] Not a Git repository."
    exit 1
fi

# Ignore execute-bit changes (chmod +x) so git pull does not fail on install.sh/update.sh
git config --local core.fileMode false

echo "Fetching latest..."
git fetch origin "$BRANCH" 2>/dev/null || git fetch

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null)

if [ "$LOCAL" == "$REMOTE" ]; then
    echo "Result: Up to date."
    exit 0
else
    echo "Result: Update Available!"
fi

echo "Pulling changes..."
if ! git pull origin "$BRANCH"; then
    echo "Resetting install.sh and update.sh (chmod changes) and retrying..."
    git checkout -- install.sh update.sh 2>/dev/null
    if ! git pull origin "$BRANCH"; then
        echo "[ERROR] git pull failed."
        exit 1
    fi
fi
chmod +x "$PROJECT_DIR/install.sh" "$PROJECT_DIR/update.sh" 2>/dev/null || true

echo "Checking system dependencies..."
sudo apt-get install -y python3-dev python3-venv liblgpio-dev numlockx libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev 2>/dev/null || true

echo "Updating Python environment..."
"$VENV_PYTHON_EXEC" -m pip install -r "$PROJECT_DIR/requirements.txt"
[ $? -ne 0 ] && { echo "[FATAL] Pip install failed."; exit 1; }

ICON_SOURCE="$PROJECT_DIR/src/assets/evolution.png"
if [ -f "$ICON_SOURCE" ]; then
    sudo cp "$ICON_SOURCE" "/usr/share/icons/growstation.png" 2>/dev/null || true
    sudo mkdir -p /usr/share/icons/hicolor/48x48/apps
    sudo cp "$ICON_SOURCE" "/usr/share/icons/hicolor/48x48/apps/growstation.png" 2>/dev/null || true
fi

echo "--- Update Complete! Please Restart. ---"
exit 0
