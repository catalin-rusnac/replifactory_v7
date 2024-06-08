#!/bin/bash

tz=$(curl -s https://ipinfo.io/timezone)
sudo ln -sf /usr/share/zoneinfo/$tz /etc/localtime
echo "Timezone updated to $(readlink /etc/localtime)"
