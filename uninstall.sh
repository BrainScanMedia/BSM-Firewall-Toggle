#!/bin/bash
# Uninstall BSM Firewall Toggle
set -e

echo "Uninstalling BSM Firewall Toggle..."

# Remove app
sudo rm -f /usr/local/bin/bsm_firewall_toggle.py
echo "Removed app."

# Remove desktop entry
sudo rm -f /usr/share/applications/bsm-firewall-toggle.desktop
sudo update-desktop-database /usr/share/applications/ 2>/dev/null || true
echo "Removed desktop entry."

# Remove icon
sudo rm -f /usr/share/icons/hicolor/scalable/apps/bsm-firewall-toggle.svg
sudo gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true
echo "Removed icon."

echo ""
echo "BSM Firewall Toggle has been uninstalled."
