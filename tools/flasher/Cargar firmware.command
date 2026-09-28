#!/bin/zsh
# Doble clic en el Finder: abre el cargador de firmware con un Python que trae tkinter.
cd "$(dirname "$0")"
for python in /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
    if [ -x "$python" ] && "$python" -c 'import tkinter' 2>/dev/null; then
        exec "$python" meridian_flasher.py
    fi
done
echo "No encontré un Python con tkinter. Instala Python desde python.org y vuelve a abrir este archivo."
read -k 1
