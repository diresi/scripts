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
}

git_mirror ~/opt/bin no_add auto_commit
git_mirror ~/work/flinkwork/office auto_add auto_commit
git_mirror ~/work/flinkwork/docker

# checkout snapshots
[[ ! -d ${SNAPSHOTS} ]] && mkdir ${SNAPSHOTS}
cd ${SNAPSHOTS}
for repo in $(find ${MOUNTPATH} -maxdepth 1 -type d -name "*.git");
do
    echo $repo
done

cd ${MOUNTPATH}/snapshots

if [[ ${MOUNTED} -eq 1 ]]; then
    echo "Unmounting $MOUNTPATH"
    umount ${MOUNTPATH}
fi

