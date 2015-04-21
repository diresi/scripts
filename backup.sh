#!/bin/bash
set -e
set -x

LABEL=FLINKBACKUP
DEVICE=/dev/disk/by-label/${LABEL}
CURDIR=${PWD}

MOUNTED=0
if [[ ! $(mount | grep ${LABEL}) ]]; then
    echo "Mounting $MOUNTPATH"
    udisksctl mount -b ${DEVICE}
    MOUNTED=1
fi

MOUNTPATH=$(udisksctl info -b ${DEVICE} | grep MountPoints | sed -e "s/ *MountPoints: *\(.*\)$/\1/")
SNAPSHOTS=${MOUNTPATH}/snapshots

function auto_add
{
    if [[ $1 = "auto_add" ]];
    then
        echo "automatic add in ${PWD}"
        git add .
    fi
}

function auto_commit
{
    if [[ $1 = "auto_commit" ]];
    then
        echo "automatic commit in ${PWD}"
        git commit -am "automatic commit" || true
    fi
}

function git_fsck
{
    REPO=$1
    cd ${REPO}
    git fsck --full --strict
}

function git_push_all
{
    REPO=$1
    AUTOADD=$2
    AUTOCOMMIT=$3
    MIRROR=${MOUNTPATH}"/"$(basename ${REPO})".git"

    cd ${REPO}
    auto_add ${AUTOADD}
    auto_commit ${AUTOCOMMIT}

    echo "mirroring ${PWD} -> ${MIRROR}"
    git push --all ${MIRROR}
    git push --tags ${MIRROR}
    git_fsck ${MIRROR}
}

git_push_all ~/opt/bin no_add auto_commit
git_push_all ~/work/flinkwork/office auto_add auto_commit
git_push_all ~/work/flinkwork/docker
cd ${CURDIR}

if [[ ${MOUNTED} -eq 1 ]]; then
    echo "Unmounting $MOUNTPATH"
    udisksctl unmount -b ${DEVICE}
fi

