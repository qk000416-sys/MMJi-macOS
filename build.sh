#!/bin/bash
set -euo pipefail
src="$(cd "$(dirname "$0")" && pwd)"
if [[ ! -d "$src/Resources/Python.framework" || ! -f "$src/Resources/AppIcon.icns" ]]; then
 bash "$src/fetch-runtime.sh"
fi
out="${1:-$src/build}"
mkdir -p "$out"
out="$(cd "$out" && pwd)"
app="$out/mm姬.app"
installer="$out/mm姬 安装器.app"
if [[ -e "$app" || -e "$installer" ]]; then echo '输出目录已存在应用，请换用空目录。' >&2; exit 1; fi
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources" "$installer/Contents/MacOS" "$installer/Contents/Resources"
cp "$src/App-Info.plist" "$app/Contents/Info.plist"
cp "$src/Installer-Info.plist" "$installer/Contents/Info.plist"
cp "$src/worker.py" "$src/pdf_unlock.py" "$app/Contents/Resources/"
cp "$src/Resources/AppIcon.icns" "$app/Contents/Resources/"
cp "$src/Resources/AppIcon.icns" "$installer/Contents/Resources/"
ditto "$src/Resources/Python.framework" "$app/Contents/Resources/Python.framework"
for arch in arm64 x86_64; do
 xcrun swiftc -runtime-compatibility-version none -disable-autolinking-runtime-compatibility-concurrency -target "$arch-apple-macos11.0" -O "$src/main.swift" -o "$temp/main-$arch"
 xcrun swiftc -runtime-compatibility-version none -disable-autolinking-runtime-compatibility-concurrency -target "$arch-apple-macos11.0" -O "$src/Installer.swift" -o "$temp/installer-$arch"
done
lipo -create "$temp/main-arm64" "$temp/main-x86_64" -output "$app/Contents/MacOS/PDFUnlock"
lipo -create "$temp/installer-arm64" "$temp/installer-x86_64" -output "$installer/Contents/MacOS/MMInstaller"
codesign --force --sign - --timestamp=none "$app"
codesign --verify --deep --strict "$app"
ditto "$app" "$installer/Contents/Resources/mm姬.app"
codesign --force --sign - --timestamp=none "$installer"
codesign --verify --deep --strict "$installer"
printf '%s\n' "$installer"
