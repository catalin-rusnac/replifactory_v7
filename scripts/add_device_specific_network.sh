#!/bin/bash

HOSTNAME=$(hostname)
ssid="replicatory$HOSTNAME"
psk="replifactory$HOSTNAME"
config_file="/etc/wpa_supplicant/wpa_supplicant.conf"

if ! grep -q "ssid=\"$ssid\"" "$config_file"; then
    {
        echo "network={"
        echo "    ssid=\"$ssid\""
        echo "    psk=\"$psk\""
        echo "    priority=100"
        echo "    key_mgmt=WPA-PSK"
        echo "}"
    } >> "$config_file"
    echo "Network configuration added to $config_file"
else
    echo "Network configuration for $ssid already exists in $config_file"
fi
