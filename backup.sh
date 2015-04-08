#!/bin/bash
set -e
#set -x

LABEL=FLINKBACKUP
MOUNTPATH=/media/${LABEL}
SNAPSHOTS=${MOUNTPATH}/snapshots

MOUNTED=0
if [[ ! $(mount | grep ${LABEL}) ]]; then
    echo "Mounting $MOUNTPATH"
    mount ${MOUNTPATH}
    MOUNTED=1
fi

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

function git_mirror
{
    REPO=$1
    AUTOADD=$2
    AUTOCOMMIT=$3
    MIRROR=${MOUNTPATH}"/"$(basename ${REPO})".git"

    cd ${REPO}
    auto_add ${AUTOADD}
    auto_commit ${AUTOCOMMIT}

    echo "mirroring ${PWD} -> ${MIRROR}"
    git push --mirror ${MIRROR}
    git_fsck ${MIRROR}
}

git_mirror ~/opt/bin no_add auto_commit
git_mirror ~/work/flinkwork/office auto_add auto_commit
git_mirror ~/work/flinkwork/docker

if [[ ${MOUNTED} -eq 1 ]]; then
    echo "Unmounting $MOUNTPATH"
    umount ${MOUNTPATH}
fi

