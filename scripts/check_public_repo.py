#!/usr/bin/env python3
"""Check the Git index for local data, vendor binaries and broken local docs links."""
import posixpath
import re
import subprocess
import sys
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit


def main():
    listing = subprocess.check_output(['git','ls-files','--cached','-z']).decode()
    names = {name for name in listing.split('\0') if name}
    if not names:
        raise SystemExit('No tracked files. Stage the intended public files before checking.')
    errors = []
    forbidden_suffixes = ('.sqlite','.sqlite-wal','.sqlite-shm','.db','.nib','.car',
                          '.dmg','.pkg','.pem','.key','.tableplusconnection')
    secret_patterns = [
        re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+/'),
        re.compile(r'/var/folders/[A-Za-z0-9_/.-]+'),
        re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),
        re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        re.compile(r'https?://[^\s/:]+:[^\s/@]+@'),
    ]
    binary_extensions = {'.png','.icns'}
    for name in sorted(names):
        path = PurePosixPath(name)
        lower = name.lower()
        if (path.parts[0] in {'analysis','.venv-re','dist','build'}
                or any(part.endswith('.app') for part in path.parts)
                or '__pycache__' in path.parts
                or lower.endswith(forbidden_suffixes)
                or lower.startswith('assets/icons/backup/')
                or path.name in {'Connections.plist','ConnectionGroups.plist','reference-craft.png'}
                or path.name == '.env' or path.name.startswith('.env.')):
            errors.append(f'{name}: private, generated or vendor file must not be tracked')
        blob = subprocess.check_output(['git','show',':'+name])
        if len(blob) > 10*1024*1024:
            errors.append(f'{name}: exceeds the public asset size limit')
        if path.suffix in binary_extensions:
            continue
        try:
            text = blob.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'{name}: unexpected binary file')
            continue
        for pattern in secret_patterns:
            if pattern.search(text):
                # Report paths only, never print matched credentials or private content.
                errors.append(f'{name}: possible private path or credential; inspect locally')
                break
        if path.suffix != '.md':
            continue
        links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text)
        links += re.findall(r'(?:src|href)="([^"]+)"',text)
        for link in links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = posixpath.normpath(posixpath.join(str(path.parent),unquote(parsed.path)))
            if destination not in names:
                errors.append(f'{name}: local link is not in the public file set: {parsed.path}')
    if errors:
        print('\n'.join(errors),file=sys.stderr)
        return 1
    print(f'Publication check passed: {len(names)} indexed files; local links resolve; no blocked content detected.')
    print('This check does not replace reviewing screenshots and the staged diff.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
