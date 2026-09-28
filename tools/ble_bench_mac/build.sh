#!/bin/zsh
# Arma MeridianBench.app junto a este archivo. Necesita Xcode (no las Command Line Tools solas).
set -e
cd "$(dirname "$0")"
export DEVELOPER_DIR=${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}
rm -rf MeridianBench.app && mkdir -p MeridianBench.app/Contents/MacOS
cp Info.plist MeridianBench.app/Contents/Info.plist
xcrun swiftc -O MeridianBench.swift -o MeridianBench.app/Contents/MacOS/MeridianBench
codesign -s - --force MeridianBench.app
echo "Listo: open -W -n $(pwd)/MeridianBench.app --args /tmp/banco.log 20 burst 5000"
