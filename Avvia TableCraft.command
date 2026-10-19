#!/bin/zsh
set -euo pipefail
task_root=${0:A:h}
research_bundle="$task_root/analysis/copies/TablePlus-Research.app"
research_profile="$task_root/analysis/runtime-profile"
[[ -x "$research_bundle/Contents/MacOS/TablePlus" ]] || {
    print -u2 'TableCraft has not been prepared. Run ./scripts/setup_tablecraft.sh first.'
    exit 1
}
mkdir -p "$research_profile"
export CFFIXED_USER_HOME="$research_profile"
if [[ ${1:-} == --offline ]]; then
    shift
    [[ -f "$research_profile/research.sb" ]] || python3 "$task_root/scripts/write_sandbox_profile.py"
    exec /usr/bin/sandbox-exec -f "$research_profile/research.sb" \
        "$research_bundle/Contents/MacOS/TablePlus" \
        -ApplePersistenceIgnoreState YES -SUEnableAutomaticChecks NO -SUAutomaticallyUpdate NO "$@"
fi
exec "$research_bundle/Contents/MacOS/TablePlus" \
    -ApplePersistenceIgnoreState YES -SUEnableAutomaticChecks NO -SUAutomaticallyUpdate NO "$@"
