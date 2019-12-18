#!/usr/bin/env bash
CURDIR=$PWD
SCRIPTDIR="$(dirname "$(readlink -f $0)")"
cd $SCRIPTDIR > /dev/null 2>&1

EXEC=decode-config

pyinstaller --log-level=DEBUG \
            --noconfirm \
            dc-build-mac.spec

if [ $? -eq 0 ]
then
    echo "Create app..."
    create-dmg dist/$EXEC.app
    echo "Copying dist/${EXEC} ../${EXEC}..."
    cp "dist/${EXEC}  0.0.0.dmg" ../${EXEC}.dmg
    echo "Well done"
    rc=0
else
    echo "Error occurred"
    rc=1
fi
popd > /dev/null 2>&1
exit $rc
