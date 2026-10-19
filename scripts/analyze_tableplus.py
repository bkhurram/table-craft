#!/usr/bin/env python3
"""Read-only static inspection of a macOS application; never executes its binaries."""
import argparse
import hashlib
import json
import plistlib
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', nargs='?', default='/Applications/TablePlus.app')
    parser.add_argument('--output', default='analysis/evidence')
    args = parser.parse_args()
    app = Path(args.app).resolve()
    output = Path(args.output).resolve()
    if output == app or app in output.parents:
        parser.error('Output must be outside the application bundle')
    output.mkdir(parents=True, exist_ok=True)
    commands = []

    def capture(name, argv):
        result = subprocess.run(argv, capture_output=True, timeout=180)
        value = result.stdout.decode('utf-8', errors='replace')
        (output / name).write_text(value)
        if result.stderr:
            (output / (name + '.stderr')).write_bytes(result.stderr)
        commands.append({'file': name, 'argv': argv, 'returncode': result.returncode})
        return value

    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    (output / 'info.json').write_text(json.dumps(info, indent=2, ensure_ascii=False))
    resources = sorted(str(p.relative_to(app)) for p in (app / 'Contents/Resources').rglob('*') if p.is_file())
    (output / 'resources.txt').write_text('\n'.join(resources) + '\n')
    summary = {'app': str(app), 'collected_at_utc': datetime.now(timezone.utc).isoformat(),
               'version': info.get('CFBundleShortVersionString'), 'build': info.get('CFBundleVersion'),
               'reference_repository': 'https://github.com/morluto/awesome-reverse-engineering',
               'reference_commit': '29449628ed591065973ab8919a6df51ba254da82',
               'binaries': [], 'resource_count': len(resources)}
    capture('signature.txt', ['codesign', '-dv', '--verbose=4', str(app)])
    capture('signature-verification.txt', ['codesign', '--verify', '--deep', '--strict', '--verbose=2', str(app)])
    capture('entitlements.plist', ['codesign', '-d', '--entitlements', ':-', str(app)])
    binaries = list((app / 'Contents/MacOS').iterdir())
    for framework in sorted((app / 'Contents/Frameworks').glob('*.framework')):
        binary = framework / framework.stem
        if binary.is_file():
            binaries.append(binary)
    for binary in binaries:
        if not binary.is_file():
            continue
        label = binary.name
        desc = capture(label + '.file.txt', ['file', str(binary)])
        deps = capture(label + '.libraries.txt', ['otool', '-arch', 'arm64', '-L', str(binary)])
        capture(label + '.headers.txt', ['otool', '-arch', 'arm64', '-hv', str(binary)])
        symbols = capture(label + '.symbols.txt', ['nm', '-arch', 'arm64', str(binary)])
        demangled = subprocess.run(['xcrun', 'swift-demangle'], input=symbols.encode(), capture_output=True, timeout=180)
        (output / (label + '.demangled.txt')).write_bytes(demangled.stdout)
        commands.append({'file': label + '.demangled.txt', 'argv': ['xcrun', 'swift-demangle'],
                         'stdin_file': label + '.symbols.txt', 'returncode': demangled.returncode})
        classes = sorted(set(re.findall(r'_OBJC_CLASS_\$_([^\s]+)', '\n'.join(x for x in symbols.splitlines() if not re.search(r'\bU\s', x)))))
        (output / (label + '.classes.txt')).write_text('\n'.join(classes) + '\n')
        if binary.parent.name == 'MacOS' or label in ('SQL', 'SQLite', 'SSHProtocol'):
            objc = capture(label + '.objc.txt', ['otool', '-arch', 'arm64', '-ov', str(binary)])
            metadata_names = sorted(set(re.findall(r'^        name\s+0x[0-9a-f]+\s+(\S+)', objc, re.MULTILINE)))
            (output / (label + '.objc-metadata-names.txt')).write_text('\n'.join(metadata_names) + '\n')
            capture(label + '.load-commands.txt', ['otool', '-arch', 'arm64', '-l', str(binary)])
            strings = capture(label + '.strings.txt', ['strings', '-arch', 'arm64', '-a', str(binary)])
            urls = sorted(set(re.findall(r'https?://[^\s<>"\x00]+', strings)))
            (output / (label + '.urls.txt')).write_text('\n'.join(urls) + '\n')
        if label == 'SQLite':
            match = re.search(r'^([0-9a-f]+) T (_\$s6SQLite12SLConnectionC7execute\S+)$', symbols, re.MULTILINE)
            if match:
                capture('SQLite.execute.lldb.txt', ['lldb', '--batch', '--arch', 'arm64', str(binary),
                        '-o', 'image lookup -a 0x' + match.group(1),
                        '-o', 'disassemble --name ' + match.group(2)[1:]])
        with binary.open('rb') as handle:
            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        summary['binaries'].append({'path': str(binary), 'sha256': digest,
                                    'size': binary.stat().st_size, 'description': desc.strip(),
                                    'defined_objc_classes': len(classes),
                                    'libraries': [x.strip() for x in deps.splitlines()[1:]]})
    (output / 'commands.json').write_text(json.dumps(commands, indent=2))
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({'output': str(output), 'binaries': len(summary['binaries']),
                      'failed_commands': [c for c in commands if c['returncode'] != 0]}, indent=2))


if __name__ == '__main__':
    main()
