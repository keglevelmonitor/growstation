#!/bin/bash
# setup.sh — Single-line installer wrapper for GrowStation
# Usage: bash <(curl -sL https://raw.githubusercontent.com/keglevelmonitor/growstation/main/setup.sh)

INSTALL_DIR="$HOME/growstation"
export DATA_DIR="$HOME/growstation-data"
export DESKTOP_FILENAME="growstation.desktop"
export APP_TITLE="GrowStation"

WHAT_TO_INSTALL="GrowStation Application and Data Directory"
CLEANUP_MODE="NONE"

echo "========================================"
echo "    GrowStation Auto-Installer"
echo "========================================"

# Handle existing installs
if [ -d "$INSTALL_DIR" ] || [ -d "$DATA_DIR" ]; then
    while true; do
        echo ""
        echo "Existing installation detected:"
        [ -d "$INSTALL_DIR" ] && echo " - App Folder: $INSTALL_DIR"
        [ -d "$DATA_DIR" ]    && echo " - Data Folder: $DATA_DIR"
        echo ""
        echo "How would you like to proceed? (Case Sensitive)"
        echo "  APP       - Reinstall App only (Keeps your existing data/settings)"
        echo "  ALL       - Reinstall App AND reset data (Fresh Install)"
        echo "  UNINSTALL - Uninstall the app and the data directory"
        echo "  EXIT      - Cancel installation"
        echo ""
        read -p "Enter selection: " choice

        if [ "$choice" == "APP" ]; then
            WHAT_TO_INSTALL="GrowStation Application"
            CLEANUP_MODE="APP"
            break
        elif [ "$choice" == "ALL" ]; then
            WHAT_TO_INSTALL="GrowStation Application and Data Directory"
            CLEANUP_MODE="ALL"
            break
        elif [ "$choice" == "UNINSTALL" ]; then
            echo "------------------------------------------"
            echo "YOU ARE ABOUT TO DELETE:"
            echo "The GrowStation application AND all user data/settings."
            echo "------------------------------------------"
            echo ""
            read -p "Type YES to UNINSTALL the app and the user data folder, or any other key to return to the menu: " confirm

            if [ "$confirm" == "YES" ]; then
                echo ""
                echo "Removing files..."
                DESKTOP_FILE="$HOME/.local/share/applications/$DESKTOP_FILENAME"
                [ -f "$DESKTOP_FILE" ] && rm "$DESKTOP_FILE" && echo " - Removed desktop shortcut"
                [ -d "$INSTALL_DIR" ] && rm -rf "$INSTALL_DIR" && echo " - Removed application directory: $INSTALL_DIR"
                [ -d "$DATA_DIR" ] && rm -rf "$DATA_DIR" && echo " - Removed data directory: $DATA_DIR"
                echo ""
                echo "Uninstallation complete."
                exit 0
            else
                echo "Uninstallation aborted. Returning to main menu..."
            fi
        elif [ "$choice" == "EXIT" ]; then
            echo "Cancelled."
            exit 0
        else
            echo "Invalid selection. Please enter APP, ALL, UNINSTALL, or EXIT."
        fi
    done
fi

# Size warning / confirmation
echo ""
echo "------------------------------------------------------------"
echo "This script will install the $WHAT_TO_INSTALL"
echo "to $INSTALL_DIR"
echo ""
echo "App will be installed to:  $INSTALL_DIR/"
echo "User data will be stored:  $DATA_DIR/"
echo "------------------------------------------------------------"
echo ""

read -p "Press Y to proceed, or any other key to cancel: " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 1
fi

# Cleanup (after confirmation)
if [ "$CLEANUP_MODE" == "APP" ]; then
    echo "Removing existing application..."
    rm -rf "$INSTALL_DIR"
elif [ "$CLEANUP_MODE" == "ALL" ]; then
    echo "Removing application and data..."
    rm -rf "$INSTALL_DIR"
    rm -rf "$DATA_DIR"
fi

# Install git if needed
if ! command -v git &> /dev/null; then
    echo "Git not found. Installing..."
    sudo apt-get update && sudo apt-get install -y git
fi

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing install..."
    cd "$INSTALL_DIR" || exit 1
    git pull --rebase
else
    echo "Cloning repository to $INSTALL_DIR..."
    git clone https://github.com/keglevelmonitor/growstation.git "$INSTALL_DIR"
    cd "$INSTALL_DIR" || exit 1
fi

# Run main installer
echo "Launching main installer..."
chmod +x install.sh
./install.sh
