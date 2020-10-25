#!/bin/bash

_action="${1:-toggle}"
_device="ELAN Touchscreen"
_prop="Device Enabled"

val=0
if [[ "$_action" = "on" ]]; then 
    val=1
elif [[ "$_action" = "toggle" ]]; then
    val=$(xinput list-props "$_device" | awk '/^\tDevice Enabled \([0-9]+\):\t[01]/ {print $NF}')
    [[ $val -eq 0 ]] && val=1 || val=0
fi

xinput --set-prop "$_device" "$_prop" $val
