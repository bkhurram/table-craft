#!/bin/zsh
set -euo pipefail
task_root=${0:A:h:h}
source_app=/Applications/TablePlus.app
check_only=0
local_controls=0
workspace_limits=0
update=0
while (( $# )); do
    case "$1" in
        --update) update=1; shift ;;
        --check) check_only=1; shift ;;
        --local-controls) local_controls=1; shift ;;
        --workspace-limits) workspace_limits=1; shift ;;
        --source)
            (( $# >= 2 )) || { print -u2 'Missing path after --source'; exit 2; }
            source_app=$2; shift 2 ;;
        -h|--help)
            print 'Usage: scripts/setup_tablecraft.sh [--check] [--update] [--local-controls | --workspace-limits] [--source /path/TablePlus.app]'
            exit 0 ;;
        *) print -u2 "Unknown option: $1"; exit 2 ;;
    esac
done
if (( local_controls && workspace_limits )); then
    print -u2 'Choose either --local-controls (818) or --workspace-limits (830).'; exit 2
fi
if (( update && local_controls )); then
    print -u2 -- '--update supports branding only. License-control modifications are not migrated.'; exit 2
fi
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || {
    print -u2 'Setup requires macOS running natively on Apple Silicon.'; exit 1
}
source "$task_root/scripts/python_runtime.sh"
tablecraft_select_python
print "Using Python: $TABLECRAFT_PYTHON ($("$TABLECRAFT_PYTHON" --version 2>&1))"
for tool in codesign ditto plutil; do
    command -v "$tool" >/dev/null || { print -u2 "Missing tool: $tool"; exit 1; }
done
[[ -x /usr/libexec/PlistBuddy ]] || { print -u2 'Missing tool: /usr/libexec/PlistBuddy'; exit 1; }
for asset in elephant-craft.png ElephantCraft.icns; do
    [[ -s "$task_root/assets/icons/$asset" ]] || {
        print -u2 "Missing asset: assets/icons/$asset. Download the complete repository ZIP again."
        exit 1
    }
done
"$TABLECRAFT_PYTHON" - "$source_app" "$local_controls" "$task_root/scripts" "$workspace_limits" <<'PY'
import hashlib, plistlib, subprocess, sys
from pathlib import Path
app = Path(sys.argv[1])
local_controls = sys.argv[2] == '1'
sys.path.insert(0, sys.argv[3])
from rebrand_tablecraft import validate_source
if not (app/'Contents/Info.plist').is_file():
    raise SystemExit('Source application was not found. Install TablePlus in /Applications, or use --source /path/TablePlus.app.')
info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
if info.get('CFBundleIdentifier') != 'com.tinyapp.TablePlus' or info.get('CFBundleExecutable') != 'TablePlus':
    raise SystemExit('The source is not an original TablePlus application bundle.')
minimum = info.get('LSMinimumSystemVersionByArchitecture', {}).get('arm64', info.get('LSMinimumSystemVersion', '0'))
current = subprocess.check_output(['/usr/bin/sw_vers', '-productVersion'], text=True).strip()
def version(value):
    return tuple((list(map(int, value.split('.'))) + [0, 0, 0])[:3])
if version(current) < version(minimum):
    raise SystemExit('This application requires macOS {} or later; found {}.'.format(minimum, current))
if local_controls and (info.get('CFBundleShortVersionString'), info.get('CFBundleVersion')) != ('27.0.2','818'):
    raise SystemExit('Found TablePlus {} ({}). --local-controls requires exactly 27.0.2 (818). Use the default setup for branding. No files were changed.'.format(
        info.get('CFBundleShortVersionString', 'unknown'), info.get('CFBundleVersion', 'unknown')))
with (app/'Contents/MacOS/TablePlus').open('rb') as handle:
    checksum = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b''):
        checksum.update(chunk)
    digest = checksum.hexdigest()
if local_controls and digest != '4547216d88fcd2868e48f31a2079da27850ace793ae79cc0fb7963d9c827c05a':
    raise SystemExit('Source executable hash does not match the supported sample. No files were changed.')
if sys.argv[4] == '1':
    from patch_workspace_limits import validate_source as validate_limits_source
    try:
        validate_limits_source(app)
    except ValueError as error:
        raise SystemExit(str(error) + '. No files were changed.')
try:
    validate_source(app)
except (OSError, ValueError, AssertionError, IndexError, KeyError, UnicodeError, subprocess.CalledProcessError) as error:
    raise SystemExit('Unsupported branding resources: {}. No files were changed.'.format(error))
print('Branding resources verified for TablePlus {} ({}).'.format(
    info.get('CFBundleShortVersionString', 'unknown'), info.get('CFBundleVersion', 'unknown')))
print('Source SHA-256: ' + digest)
if sys.argv[4] == '1':
    print('Exact source version and SHA-256 verified for tab/workspace changes.')
elif local_controls:
    print('Exact source version and SHA-256 verified for local controls.')
else:
    print('Branding setup: application code and license controls are unchanged. Other source builds require runtime verification on your Mac.')
PY
if (( check_only )); then
    print 'Preflight passed. Check-only mode did not create or modify an application.'
    exit 0
fi
research_bundle="$task_root/analysis/copies/TablePlus-Research.app"
if (( ! update )) && [[ -e "$research_bundle" ]]; then
    print -u2 "A local copy already exists at: $research_bundle"
    print -u2 'Setup will not overwrite it. If an older setup failed, move that bundle aside and retry; keep analysis/runtime-profile.'
    exit 1
fi
mkdir -p "$task_root/analysis/copies" "$task_root/analysis/evidence/feature-controls"
setup_lock="$task_root/analysis/copies/.setup-lock"
mkdir "$setup_lock" 2>/dev/null || {
    print -u2 "Another setup may be running. If it has stopped, remove this empty lock directory: $setup_lock"
    exit 1
}
staging_dir=''
previous_bundle=''
cleanup() {
    local result=$?
    if [[ -n "$previous_bundle" && ! -e "$research_bundle" ]]; then
        mv "$previous_bundle" "$research_bundle"
    fi
    [[ -z "$staging_dir" ]] || rm -rf -- "$staging_dir"
    rmdir "$setup_lock"
    return "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
check_stopped() {
    local running=0
    local process_pattern
    process_pattern='[/]TablePlus-Research[.]app/Contents/MacOS/TablePlus'
    pgrep -f "$process_pattern" >/dev/null || running=$?
    if (( running != 1 )); then
        print -u2 'Close TablePlus/TableCraft research copy before updating. Process inspection must be available.'
        return 1
    fi
}
if (( update )); then
    check_stopped || exit 1
    profile_backup=$("$TABLECRAFT_PYTHON" "$task_root/scripts/profile_manager.py" snapshot)
    print "Profile backup: $profile_backup"
fi
staging_dir=$(mktemp -d "$task_root/analysis/copies/.tablecraft-setup.XXXXXX")
export TABLECRAFT_BUNDLE="$staging_dir/TablePlus-Research.app"
print 'Copying the application and applying branding…'
ditto "$source_app" "$TABLECRAFT_BUNDLE"
if (( local_controls )); then
    "$TABLECRAFT_PYTHON" "$task_root/scripts/prepare_research_copy.py"
fi
if (( workspace_limits )); then
    "$TABLECRAFT_PYTHON" "$task_root/scripts/patch_workspace_limits.py"
fi
"$TABLECRAFT_PYTHON" - "$TABLECRAFT_BUNDLE" <<'PY'
import plistlib, sys
from pathlib import Path
p = Path(sys.argv[1])/'Contents/Info.plist'
info = plistlib.loads(p.read_bytes())
info['CFBundleIdentifier'] = 'com.tinyapp.TablePlus.Research'
for key in ('SUEnableAutomaticChecks','SUAutomaticallyUpdate','SUAllowsAutomaticUpdates'):
    info[key] = False
p.write_bytes(plistlib.dumps(info))
PY
"$TABLECRAFT_PYTHON" "$task_root/scripts/rebrand_tablecraft.py"
/bin/zsh "$task_root/scripts/install_craft_icon.sh" "$task_root/assets/icons/elephant-craft.png"
if (( update )); then
    check_stopped || exit 1
fi
if [[ -e "$research_bundle" ]]; then
    (( update )) || { print -u2 'A local copy appeared during setup; it will not be overwritten.'; exit 1; }
    backup_dir=$(mktemp -d "$task_root/analysis/copies/previous.XXXXXX")
    previous_bundle="$backup_dir/TablePlus-Research.app"
    mv "$research_bundle" "$previous_bundle"
fi
mv "$TABLECRAFT_BUNDLE" "$research_bundle"
[[ -z "$previous_bundle" ]] || print "Previous application preserved at: $previous_bundle"
print 'TableCraft is ready. Start it with ./"Avvia TableCraft.command".'
