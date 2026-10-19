#!/bin/zsh
set -euo pipefail
task_root=${0:A:h:h}
source_app=/Applications/TablePlus.app
check_only=0
local_controls=0
while (( $# )); do
    case "$1" in
        --check) check_only=1; shift ;;
        --local-controls) local_controls=1; shift ;;
        --source)
            (( $# >= 2 )) || { print -u2 'Missing path after --source'; exit 2; }
            source_app=$2; shift 2 ;;
        -h|--help)
            print 'Usage: scripts/setup_tablecraft.sh [--check] [--local-controls] [--source /path/TablePlus.app]'
            exit 0 ;;
        *) print -u2 "Unknown option: $1"; exit 2 ;;
    esac
done
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || {
    print -u2 'Setup requires macOS running natively on Apple Silicon.'; exit 1
}
for tool in python3 codesign ditto sips iconutil plutil xcrun; do
    command -v "$tool" >/dev/null || { print -u2 "Missing tool: $tool"; exit 1; }
done
python3 - "$source_app" <<'PY'
import hashlib, plistlib, sys
from pathlib import Path
if sys.version_info < (3, 11):
    raise SystemExit('Python 3.11 or later is required.')
app = Path(sys.argv[1])
if not (app/'Contents/Info.plist').is_file():
    raise SystemExit('Source application was not found.')
info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
if (info.get('CFBundleShortVersionString'), info.get('CFBundleVersion')) != ('27.0.2','818'):
    raise SystemExit('Supported source: TablePlus 27.0.2 (818). No files were changed.')
with (app/'Contents/MacOS/TablePlus').open('rb') as handle:
    digest = hashlib.file_digest(handle, 'sha256').hexdigest()
if digest != '4547216d88fcd2868e48f31a2079da27850ace793ae79cc0fb7963d9c827c05a':
    raise SystemExit('Source executable hash does not match the supported sample. No files were changed.')
print('Source version and SHA-256 verified.')
PY
if (( check_only )); then
    print 'Preflight passed. Check-only mode did not create or modify an application.'
    exit 0
fi
research_bundle="$task_root/analysis/copies/TablePlus-Research.app"
[[ ! -e "$research_bundle" ]] || {
    print -u2 'A local copy already exists. Keep it and its profile; setup will not overwrite it.'; exit 1
}
mkdir -p "$task_root/analysis/copies" "$task_root/analysis/evidence/feature-controls"
codesign -d --entitlements :- "$source_app" > "$task_root/analysis/evidence/entitlements.plist"
plutil -lint "$task_root/analysis/evidence/entitlements.plist" >/dev/null
ditto "$source_app" "$research_bundle"
if (( local_controls )); then
    python3 "$task_root/scripts/prepare_research_copy.py"
fi
python3 - "$research_bundle" <<'PY'
import plistlib, sys
from pathlib import Path
p = Path(sys.argv[1])/'Contents/Info.plist'
info = plistlib.loads(p.read_bytes())
info['CFBundleIdentifier'] = 'com.tinyapp.TablePlus.Research'
for key in ('SUEnableAutomaticChecks','SUAutomaticallyUpdate','SUAllowsAutomaticUpdates'):
    info[key] = False
p.write_bytes(plistlib.dumps(info))
PY
python3 "$task_root/scripts/rebrand_tablecraft.py"
"$task_root/scripts/install_craft_icon.sh" "$task_root/assets/icons/elephant-craft.png"
python3 "$task_root/scripts/write_sandbox_profile.py"
print 'TableCraft is ready. Start it with ./"Avvia TableCraft.command".'
