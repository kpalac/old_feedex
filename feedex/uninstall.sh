#!/bin/bash



# Run this as root to uninstall Feedex from your system

printf "Uninstalling FEEDEX ...\n"

sudo rm -r "/usr/share/feedex"
sudo rm "/usr/bin/feedex"
sudo rm "/usr/bin/feedex_clip"

if [[ -f "/usr/share/applications/feedex.desktop" ]]; then
    sudo rm "/usr/share/applications/feedex.desktop"
fi

if [[ "$1" == "with_config" ]]; then
    sudo rm /etc/feedex.conf
    sudo rm /etc/feedex_gui.conf
fi



printf "\n\nDone...\n"