#!/bin/bash
set -euo pipefail
src="$(cd "$(dirname "$0")" && pwd)"
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
curl --fail --location --retry 3 'https://github.com/qk000416-sys/MMJi-macOS/releases/download/v1.3.2/MMJi-v1.3.2-Source.zip' -o "$temp/source.zip"
printf '%s  %s\n' 'f58aa5241654616b0ef03495b756335cb61fb69d4dc5387dba966321c1e437c1' "$temp/source.zip" | shasum -a 256 -c -
ditto -x -k "$temp/source.zip" "$temp/extracted"
mkdir -p "$src/Resources"
ditto "$temp/extracted/MM-Source/Resources/Python.framework" "$src/Resources/Python.framework"
cp "$temp/extracted/MM-Source/Resources/AppIcon.icns" "$src/Resources/AppIcon.icns"
codesign --verify --deep --strict "$src/Resources/Python.framework"
