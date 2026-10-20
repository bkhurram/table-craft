#!/bin/zsh
set -euo pipefail
task_root=${0:A:h}
research_bundle="$task_root/analysis/copies/TablePlus-Research.app"
source "$task_root/scripts/python_runtime.sh"
tablecraft_select_python
if [[ -e "$task_root/runtime" || -L "$task_root/runtime" ]]; then
    research_bundle=$("$TABLECRAFT_PYTHON" "$task_root/scripts/portable_runtime.py" verify)
fi
research_profile=$("$TABLECRAFT_PYTHON" "$task_root/scripts/profile_manager.py" prepare)
export TABLECRAFT_PROFILE="$research_profile"
if [[ ! -x "$research_bundle/Contents/MacOS/TablePlus" ]]; then
    print 'First launch: no embedded runtime found; preparing TableCraft from /Applications/TablePlus.app…'
    /bin/zsh "$task_root/scripts/setup_tablecraft.sh" || {
        print -u2 'Setup failed. Resolve the requirement shown above, then open this launcher again.'
        exit 1
    }
fi
[[ -x "$research_bundle/Contents/MacOS/TablePlus" ]] || {
    print -u2 'Setup did not create a runnable application.'
    exit 1
}
if [[ $(/usr/libexec/PlistBuddy -c 'Print :CFBundleName' "$research_bundle/Contents/Info.plist" 2>/dev/null) != TableCraft ]] \
    || ! /usr/bin/codesign --verify --deep --strict "$research_bundle"; then
    print -u2 "The local application is incomplete or its signature is invalid: $research_bundle"
    print -u2 'Move that bundle aside and reopen the launcher to prepare a new copy. Keep the user profile; see docs/setup.md.'
    exit 1
fi
mkdir -p "$research_profile"
export CFFIXED_USER_HOME="$research_profile"
if [[ ${1:-} == --offline ]]; then
    shift
    "$TABLECRAFT_PYTHON" "$task_root/scripts/write_sandbox_profile.py"
    exec /usr/bin/sandbox-exec -f "$research_profile/research.sb" \
        "$research_bundle/Contents/MacOS/TablePlus" \
        -ApplePersistenceIgnoreState YES -SUEnableAutomaticChecks NO -SUAutomaticallyUpdate NO "$@"
fi
exec "$research_bundle/Contents/MacOS/TablePlus" \
    -ApplePersistenceIgnoreState YES -SUEnableAutomaticChecks NO -SUAutomaticallyUpdate NO "$@"
