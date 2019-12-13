#!/usr/bin/env bash
EXEC=decode-config

pyinstaller --log-level=DEBUG \
            --noconfirm \
            dc-build-mac.spec

if [ $? -eq 0 ]
then
  create-dmg dist/$EXEC.app
  cp "dist/${EXEC}  0.0.0.dmg" ../${EXEC}.dmg
fi
