#!/usr/bin/env bash
EXEC=decode-config

pyinstaller --log-level=DEBUG \
            --noconfirm \
            dc-build-linux.spec

if [ $? -eq 0 ]
then
    echo "Copying dist/${EXEC} ../${EXEC}"
    cp dist/${EXEC} ../ 
fi
