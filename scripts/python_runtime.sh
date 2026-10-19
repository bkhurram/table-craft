#!/bin/zsh
# Source this file to select one compatible interpreter for the whole setup.
tablecraft_select_python() {
    local candidate
    local -a candidates
    if [[ -n ${TABLECRAFT_PYTHON:-} ]]; then
        candidates=("$TABLECRAFT_PYTHON")
    else
        candidates=("${commands[python3]:-}" /opt/homebrew/bin/python3
            /usr/local/bin/python3
            /Library/Frameworks/Python.framework/Versions/Current/bin/python3
            /usr/bin/python3)
    fi
    for candidate in "${candidates[@]}"; do
        [[ -n "$candidate" && -x "$candidate" ]] || continue
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
            export TABLECRAFT_PYTHON="$candidate"
            return 0
        fi
    done
    print -u2 'Python 3.9 or later was not found. Install Python 3 from python.org, then reopen the launcher.'
    print -u2 'To select an existing interpreter, set TABLECRAFT_PYTHON to its executable path.'
    return 1
}
