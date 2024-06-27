#!/bin/bash

HOSTNAME=$(hostname)
ssid="replifactory$HOSTNAME"
psk="replifactory$HOSTNAME"
config_file="/etc/wpa_supplicant/wpa_supplicant.conf"

if ! grep -q "ssid=\"$ssid\"" "$config_file"; then
    {
        echo ""
        echo "network={"
        echo "    ssid=\"$ssid\""
        echo "    psk=\"$psk\""
        echo "    priority=100"
        echo "    key_mgmt=WPA-PSK"
        echo "}\n"
    } >> "$config_file"
    echo "Network configuration added to $config_file"
else
    echo "Network configuration for $ssid already exists in $config_file"
fi

# add AggieAir open network
if ! grep -q "ssid=\"AggieAir\"" "$config_file"; then
    {
        echo ""
        echo "network={"
        echo "    ssid=\"AggieAir\""
        echo "    priority=7"
        echo "    key_mgmt=NONE"
        echo "}\n"
    } >> "$config_file"
    echo "Network configuration added to $config_file"
else
    echo "Network configuration for AggieAir already exists in $config_file"
fi