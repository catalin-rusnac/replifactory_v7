#!/bin/bash
tz=$(curl -s https://ipinfo.io/timezone)
echo "Setting timezone to $tz"
sudo rm /etc/localtime
sudo ln -sf /usr/share/zoneinfo/$tz /etc/localtime
readlink /etc/localtime

