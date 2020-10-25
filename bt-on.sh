#!/bin/bash
set -Eeuxo pipefail

echo -e "power on" | bluetoothctl
sleep 1
echo -e "scan on" | bluetoothctl
