#!/bin/bash
echo "Current timezone is $(readlink /etc/localtime)"
tz=$(curl -s https://ipinfo.io/timezone)
# if current timezone is different from detected timezone
if [ $(readlink /etc/localtime) == "/usr/share/zoneinfo/$tz" ]; then
  echo "Timezone is already up to date"
  exit 0
fi

sudo rm /etc/localtime
sudo ln -sf /usr/share/zoneinfo/$tz /etc/localtime
echo "New timezone is $(readlink /etc/localtime)"

