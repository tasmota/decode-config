#!/usr/bin/env bash
# needs brew (https://brew.sh/) and "brew install coreutils"
CURDIR=$PWD
SCRIPTDIR="$(dirname "$(readlink -f $0)")"
pushd $SCRIPTDIR > /dev/null 2>&1

EXEC=decode-config_mac

pyinstaller --noconfirm \
            dc-build-linux.spec

if [ $? -eq 0 ]
then
    echo "Copying dist/${EXEC} ../${EXEC}..."
    cp dist/${EXEC} ../${EXEC}
    echo "Well done"
    rc=0
else
    echo "Error occurred"
    rc=1
fi
popd > /dev/null 2>&1
exit $rc
