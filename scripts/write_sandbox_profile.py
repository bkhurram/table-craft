#!/usr/bin/env python3
"""Create the optional offline test profile using this machine's home path."""
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    profile = root / 'analysis/runtime-profile'
    profile.mkdir(parents=True, exist_ok=True)
    home = Path.home()
    text = '(version 1)\n(allow default)\n(deny network*)\n'
    for path in [home/'Library/Application Support/com.tinyapp.TablePlus',
                 home/'Library/Application Support/TablePlus', home/'Library/Keychains',
                 home/'Library/Preferences/com.tinyapp.TablePlus.plist']:
        text += '(deny file-read* file-write* (subpath '+json.dumps(str(path))+'))\n'
    text += '(deny file-write* (subpath "/Applications/TablePlus.app"))\n'
    (profile/'research.sb').write_text(text)
    print('Offline profile created in analysis/runtime-profile/research.sb')


if __name__ == '__main__':
    main()
