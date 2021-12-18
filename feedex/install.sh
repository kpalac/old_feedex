#!/bin/bash



# Run this as root to install Feedex on your system

printf "Installing FEEDEX ...\n\n"

sudo mkdir -p "/usr/share/feedex/data"

sudo cp -r ./data "/usr/share/feedex"
sudo cp -r ./feedex "/usr/share/feedex"

sudo cp ./scripts/feedex "/usr/bin/feedex"


sudo cp ./data/examples/config /etc/feedex.conf

if [[ "$1" != "no_gui" ]]; then

    sudo cp ./scripts/feedex_clip /usr/bin/feedex_clip
    sudo cp ./data/feedex.desktop /usr/share/applications/feedex.desktop
    sudo chmod 655 /usr/share/applications/feedex.desktop
    if [[ ! -d /usr/share/icons/hicolor/symbolic/apps ]]; then
        sudo mkdir /usr/share/icons/hicolor/symbolic/apps
    fi
    sudo cp ./data/icons/*.svg /usr/share/icons/hicolor/symbolic/apps
    sudo chmod 644 /usr/share/icons/hicolor/symbolic/apps/*.svg

fi

sudo chmod 655 /etc/feedex.conf
sudo chmod 755 /usr/bin/feedex*
sudo find /usr/share/feedex/ -type d -exec chmod 755 {} +
sudo find /usr/share/feedex/ -type f -exec chmod 644 {} +


# Install dependencies
if [[ "$1" != "no_deps" ]]; then

    printf "Installing dependencies ...\n"

    sudo apt-get install python3
    sudo apt-get install pip3
    sudo apt-get install -y python3-feedparser

    sudo pip install feedparser
    sudo pip install urllib3
    sudo pip install pysqlite3
    sudo pip install python-dateutil
    sudo pip install snowballstemmer
    sudo pip install Pyphen

    if [[ "$1" != "no_gui" ]]; then
        sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
        sudo apt-get install xclip libnotify-bin notify-osd xdotool
        sudo pip3 install pillow
    fi
fi

printf "\n\nDone...\n"
