#!/bin/zsh
set -euo pipefail
task_root=${0:A:h:h}
icon_source=${1:?Pass the generated square PNG path}
icon_folder="$task_root/assets/icons"
iconset="$icon_folder/ElephantCraft.iconset"
research_bundle=${TABLECRAFT_BUNDLE:-"$task_root/analysis/copies/TablePlus-Research.app"}
mkdir -p "$icon_folder/backup"
if [[ ${icon_source:A} != "$icon_folder/elephant-craft.png" ]]; then
    cp "$icon_source" "$icon_folder/elephant-craft.png"
fi
if [[ ! -f "$icon_folder/backup/Info.plist" ]]; then
    cp "$research_bundle/Contents/Info.plist" "$icon_folder/backup/Info.plist"
    cp "$research_bundle/Contents/Resources/AppIcon.icns" "$icon_folder/backup/AppIcon.icns"
fi
if [[ ${icon_source:A} != "$icon_folder/elephant-craft.png" || ! -s "$icon_folder/ElephantCraft.icns" ]]; then
    mkdir -p "$iconset"
    for icon_size in 16 32 128 256 512; do
        /usr/bin/sips -z "$icon_size" "$icon_size" "$icon_folder/elephant-craft.png" \
            --out "$iconset/icon_${icon_size}x${icon_size}.png" >/dev/null
        double_size=$((icon_size * 2))
        /usr/bin/sips -z "$double_size" "$double_size" "$icon_folder/elephant-craft.png" \
            --out "$iconset/icon_${icon_size}x${icon_size}@2x.png" >/dev/null
    done
    /usr/bin/iconutil -c icns "$iconset" -o "$icon_folder/ElephantCraft.icns"
fi
cp "$icon_folder/ElephantCraft.icns" "$research_bundle/Contents/Resources/CraftIcon.icns"
/usr/libexec/PlistBuddy -c 'Set :CFBundleIconFile CraftIcon.icns' "$research_bundle/Contents/Info.plist"
if /usr/libexec/PlistBuddy -c 'Print :CFBundleIconName' "$research_bundle/Contents/Info.plist" >/dev/null 2>&1; then
    /usr/libexec/PlistBuddy -c 'Delete :CFBundleIconName' "$research_bundle/Contents/Info.plist"
fi
/usr/bin/codesign --force --deep --sign - --options runtime \
    --preserve-metadata=entitlements "$research_bundle"
/usr/bin/codesign --verify --deep --strict "$research_bundle"
touch "$research_bundle"
print "Installed icon: $icon_folder/ElephantCraft.icns"
