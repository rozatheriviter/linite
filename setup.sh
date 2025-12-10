#!/bin/bash
echo "Installing dependencies for Linite..."
sudo apt update
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 flatpak
echo "Dependencies installed."

echo "You can now run linite with: python3 linite.py"
