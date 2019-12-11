#!/usr/bin/env bash
#rm -fr build dist
VERSION=1.0
NAME=decode-config

pyinstaller --log-level=DEBUG \
            --noconfirm \
            dc-build-linux.spec

mv dist/decode-config ./
