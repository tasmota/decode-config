#!/usr/bin/env bash
#rm -fr build dist
VERSION=1.0
NAME=decode-config

pyinstaller --log-level=DEBUG \
            --noconfirm \
            dc-build-mac.spec

#https://github.com/sindresorhus/create-dmg
create-dmg dist/$NAME-$VERSION.app
mv "$NAME-$VERSION 0.0.0.dmg" dist/$NAME-$VERSION.dmg
