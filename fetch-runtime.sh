#!/bin/bash
set -euo pipefail
src="$(cd "$(dirname "$0")" && pwd)"
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
curl --fail --location --retry 3 'https://github.com/qk000416-sys/MMJi-macOS/releases/download/v1.3.2/MMJi-v1.3.2-Source.zip' -o "$temp/source.zip"
printf '%s  %s\n' 'b29b4cbdbb1d320c8d22e75e9593d17e8fd0851d3259df03f4ef17010a65753d' "$temp/source.zip" | shasum -a 256 -c -
ditto -x -k "$temp/source.zip" "$temp/extracted"
mkdir -p "$src/Resources"
ditto "$temp/extracted/MM-Source/Resources/Python.framework" "$src/Resources/Python.framework"
cp "$temp/extracted/MM-Source/Resources/AppIcon.icns" "$src/Resources/AppIcon.icns"
codesign --verify --deep --strict "$src/Resources/Python.framework"
