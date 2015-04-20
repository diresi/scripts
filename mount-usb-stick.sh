#!/bin/bash
set -e

function udiskctl_action {
    action="$1"
    udisksctl ${action} -b /dev/disk/by-label/FLINKBACKUP
}

arg="$1"
case ${arg} in
mount)
    ;;
unmount)
    ;;
*)
    echo "Usage: $0 {mount|unmount}"
    exit 1
    ;;
esac

udiskctl_action ${arg}
