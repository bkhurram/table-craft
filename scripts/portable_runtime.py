#!/usr/bin/env python3
"""Seal and package the existing customized runtime without rebuilding or patching it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def inventory(bundle):
    bundle = Path(bundle)
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError('Runtime must be a real application directory')
    result = {}
    for path in sorted(bundle.rglob('*')):
        relative = path.relative_to(bundle).as_posix()
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            target = os.readlink(path)
            if os.path.isabs(target) or not path.resolve().is_relative_to(bundle.resolve()):
                raise ValueError('External runtime symlink: ' + relative)
            result[relative] = dict(link=target)
        elif path.is_file():
            result[relative] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), mode=mode)
        elif path.is_dir():
            result[relative] = dict(directory=True, mode=mode)
        else:
            raise ValueError('Unsupported runtime entry: ' + relative)
    return result


def overrides(bundle):
    from macho_inspect import MachO
    from patch_workspace_limits import (GATES, SECONDARY_TAB, TRIAL_NOTIFICATION_GATES,
                                        TRIAL_WELCOME_ARGUMENTS, FILTER_GATES)
    info = plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
    if (info.get('CFBundleName'), info.get('CFBundleVersion')) != ('TableCraft', '830'):
        raise ValueError('Portable runtime requires the existing customized TableCraft build 830')
    macho = MachO(bundle/'Contents/MacOS/TablePlus')
    groups = {
        'tabs_and_windows': (*GATES, SECONDARY_TAB),
        'filters': tuple((a, d, r) for a, d, _, r in FILTER_GATES),
        'trial_notifications': TRIAL_NOTIFICATION_GATES,
    }
    checks = {}
    for name, entries in groups.items():
        checks[name] = all(macho.read(a, 4) == struct.pack('<I', 0x14000000 | (((d-a)//4) & 0x3ffffff))
                           for a, d, _ in entries)
    checks['trial_welcome'] = all(macho.read(a, 4) == bytes.fromhex('22008052')
                                 for a in TRIAL_WELCOME_ARGUMENTS)
    from patch_keychain_identity import identity
    if identity(bundle) == 'isolated':
        checks['keychain_identity'] = True
    checks['logo'] = (info.get('CFBundleIconFile') == 'CraftIcon.icns'
                      and (bundle/'Contents/Resources/CraftIcon.icns').read_bytes() == (ROOT/'assets/icons/ElephantCraft.icns').read_bytes()
                      and (bundle/'Contents/Resources/CraftElephant.png').read_bytes() == (ROOT/'assets/icons/elephant-craft.png').read_bytes())
    if not all(checks.values()):
        raise ValueError('Missing existing overrides: ' + ', '.join(k for k, v in checks.items() if not v))
    return checks


def signature(bundle):
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)


def verify(runtime):
    runtime = Path(runtime)
    manifest = json.loads((runtime/'manifest.json').read_text())
    if manifest.get('format') != 1 or manifest.get('bundle') != 'TableCraft.app':
        raise ValueError('Unsupported runtime manifest')
    bundle = runtime/'TableCraft.app'
    if inventory(bundle) != manifest['entries']:
        raise ValueError('Runtime integrity mismatch; restore the complete portable runtime')
    signature(bundle)
    if 'mcp_settings' in manifest:
        from patch_mcp_settings import state
        if state(bundle) != 'TableCraft':
            raise ValueError('MCP settings branding mismatch')
    if 'mcp_registration' in manifest:
        from patch_mcp_registration import state as registration_state
        if registration_state(bundle) != 'TableCraft':
            raise ValueError('MCP registration branding mismatch')
    if 'mcp_isolation' in manifest:
        from patch_mcp_isolation import state as mcp_isolation_state
        if mcp_isolation_state(bundle) != 'isolated':
            raise ValueError('MCP isolation mismatch')
    if overrides(bundle) != manifest['overrides']:
        raise ValueError('Runtime override mismatch')
    return bundle


def embed(source, destination):
    source, destination = Path(source).resolve(), Path(destination)
    if destination.exists():
        raise ValueError('Runtime already exists; it will not be overwritten. Move it aside to replace it explicitly.')
    signature(source)
    overrides(source)
    entries = inventory(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.tablecraft-runtime-', dir=destination.parent) as temp:
        stage = Path(temp)/'runtime'
        stage.mkdir()
        subprocess.run(['/usr/bin/ditto', str(source), str(stage/'TableCraft.app')], check=True)
        staged_bundle = stage/'TableCraft.app'
        if inventory(staged_bundle) != entries:
            raise ValueError('Source runtime changed while copying')
        from patch_keychain_identity import identity, patch, SERVICE, LABEL
        keychain = None
        mcp_renamed = ensure_mcp_name(staged_bundle)
        changed_keychain = False
        if identity(staged_bundle) == 'legacy':
            changes = patch(staged_bundle)
            changed_keychain = True
            keychain = dict(service=SERVICE, label=LABEL, migrated_credentials=False,
                            architectures=['arm64', 'x86_64'], changes=changes)
        elif (source.parent/'manifest.json').is_file():
            keychain = json.loads((source.parent/'manifest.json').read_text()).get('keychain')
        if mcp_renamed or changed_keychain:
            subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                            '--preserve-metadata=entitlements', str(staged_bundle)], check=True)
        info = plistlib.loads((source/'Contents/Info.plist').read_bytes())
        manifest = dict(format=1, bundle='TableCraft.app', version=info['CFBundleShortVersionString'],
                        build=info['CFBundleVersion'], overrides=overrides(staged_bundle), entries=inventory(staged_bundle))
        from patch_mcp_registration import state as registration_state
        if registration_state(staged_bundle) == 'TableCraft':
            manifest['mcp_registration'] = dict(name='TableCraft')
        from patch_mcp_isolation import state as mcp_isolation_state, BUNDLE_ID, TOKEN_SERVICE, DEFAULT_PORT
        if mcp_isolation_state(staged_bundle) == 'isolated':
            manifest['mcp_isolation'] = dict(bundle_id=BUNDLE_ID, token_service=TOKEN_SERVICE, default_port=DEFAULT_PORT)
        manifest['mcp_executable'] = 'Contents/MacOS/tablecraft-mcp'
        if keychain:
            manifest['keychain'] = keychain
        from patch_mcp_settings import state as mcp_settings_state
        if mcp_settings_state(staged_bundle) == 'TableCraft':
            manifest['mcp_settings'] = dict(branding='TableCraft', helper='tablecraft-mcp')
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
        verify(stage)
        stage.rename(destination)
    return destination


def ensure_mcp_name(bundle):
    directory = Path(bundle)/'Contents/MacOS'
    previous, current = directory/'tableplus-mcp', directory/'tablecraft-mcp'
    if current.exists() or current.is_symlink():
        if (current.is_file() and not current.is_symlink() and os.access(current, os.X_OK)
                and previous.is_symlink() and os.readlink(previous) == 'tablecraft-mcp'):
            return False
        raise ValueError('Unexpected MCP executable or compatibility link; no replacement made')
    if not previous.is_file() or previous.is_symlink() or not os.access(previous, os.X_OK):
        raise ValueError('Expected a runnable original MCP helper')
    previous.rename(current)
    previous.symlink_to(current.name)
    return True


def rename_mcp(runtime):
    runtime = Path(runtime).resolve()
    bundle = verify(runtime)
    if (bundle/'Contents/MacOS/tablecraft-mcp').exists():
        ensure_mcp_name(bundle)
        return runtime
    with tempfile.TemporaryDirectory(prefix='.tablecraft-mcp-', dir=runtime.parent) as temp:
        stage = Path(temp)/'runtime'
        subprocess.run(['/usr/bin/ditto', str(runtime), str(stage)], check=True)
        staged_bundle = stage/'TableCraft.app'
        ensure_mcp_name(staged_bundle)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                        '--preserve-metadata=entitlements', str(staged_bundle)], check=True)
        manifest = json.loads((stage/'manifest.json').read_text())
        manifest['entries'] = inventory(staged_bundle)
        from patch_mcp_registration import state as registration_state
        if registration_state(staged_bundle) == 'TableCraft':
            manifest['mcp_registration'] = dict(name='TableCraft')
        from patch_mcp_isolation import state as mcp_isolation_state, BUNDLE_ID, TOKEN_SERVICE, DEFAULT_PORT
        if mcp_isolation_state(staged_bundle) == 'isolated':
            manifest['mcp_isolation'] = dict(bundle_id=BUNDLE_ID, token_service=TOKEN_SERVICE, default_port=DEFAULT_PORT)
        manifest['mcp_executable'] = 'Contents/MacOS/tablecraft-mcp'
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
        verify(stage)
        backup_root = ROOT/'analysis/runtime-backups'
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='before-mcp-path-', dir=backup_root))/'runtime'
        runtime.rename(backup)
        try:
            stage.rename(runtime)
        except BaseException:
            backup.rename(runtime)
            raise
        print('Previous runtime preserved at: '+str(backup))
    return runtime


def brand_mcp_settings(runtime):
    from patch_mcp_settings import state, patch
    runtime = Path(runtime).resolve()
    bundle = verify(runtime)
    if state(bundle) == 'TableCraft':
        return runtime
    with tempfile.TemporaryDirectory(prefix='.tablecraft-mcp-settings-', dir=runtime.parent) as temp:
        stage = Path(temp)/'runtime'
        subprocess.run(['/usr/bin/ditto', str(runtime), str(stage)], check=True)
        staged_bundle = stage/'TableCraft.app'
        changes = patch(staged_bundle)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                        '--preserve-metadata=entitlements', str(staged_bundle)], check=True)
        manifest = json.loads((stage/'manifest.json').read_text())
        manifest['entries'] = inventory(staged_bundle)
        manifest['mcp_settings'] = dict(branding='TableCraft', helper='tablecraft-mcp', changes=changes)
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
        verify(stage)
        backup_root = ROOT/'analysis/runtime-backups'
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='before-mcp-settings-', dir=backup_root))/'runtime'
        runtime.rename(backup)
        try:
            stage.rename(runtime)
        except BaseException:
            backup.rename(runtime)
            raise
        print('Previous runtime preserved at: '+str(backup))
    return runtime


def brand_mcp_registration(runtime):
    from patch_mcp_registration import state, patch
    runtime = Path(runtime).resolve()
    bundle = verify(runtime)
    if state(bundle) == 'TableCraft':
        return runtime
    with tempfile.TemporaryDirectory(prefix='.tablecraft-mcp-registration-', dir=runtime.parent) as temp:
        stage = Path(temp)/'runtime'
        subprocess.run(['/usr/bin/ditto', str(runtime), str(stage)], check=True)
        staged_bundle = stage/'TableCraft.app'
        changes = patch(staged_bundle)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                        '--preserve-metadata=entitlements', str(staged_bundle)], check=True)
        manifest = json.loads((stage/'manifest.json').read_text())
        manifest['entries'] = inventory(staged_bundle)
        manifest['mcp_registration'] = dict(name='TableCraft', changes=changes)
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
        verify(stage)
        backup_root = ROOT/'analysis/runtime-backups'
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='before-mcp-registration-', dir=backup_root))/'runtime'
        runtime.rename(backup)
        try:
            stage.rename(runtime)
        except BaseException:
            backup.rename(runtime)
            raise
        print('Previous runtime preserved at: '+str(backup))
    return runtime


def isolate_mcp(runtime):
    from patch_mcp_isolation import state, patch, BUNDLE_ID, TOKEN_SERVICE, DEFAULT_PORT
    runtime = Path(runtime).resolve()
    bundle = verify(runtime)
    if state(bundle) == 'isolated':
        return runtime
    with tempfile.TemporaryDirectory(prefix='.tablecraft-mcp-isolation-', dir=runtime.parent) as temp:
        stage = Path(temp)/'runtime'
        subprocess.run(['/usr/bin/ditto', str(runtime), str(stage)], check=True)
        staged_bundle = stage/'TableCraft.app'
        changes = patch(staged_bundle)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                        '--preserve-metadata=entitlements', str(staged_bundle/'Contents/MacOS/tablecraft-mcp')], check=True)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                        '--preserve-metadata=entitlements', str(staged_bundle)], check=True)
        manifest = json.loads((stage/'manifest.json').read_text())
        manifest['entries'] = inventory(staged_bundle)
        manifest['mcp_isolation'] = dict(bundle_id=BUNDLE_ID, token_service=TOKEN_SERVICE, default_port=DEFAULT_PORT, changes=changes)
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
        verify(stage)
        backup_root = ROOT/'analysis/runtime-backups'
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='before-mcp-isolation-', dir=backup_root))/'runtime'
        runtime.rename(backup)
        try:
            stage.rename(runtime)
        except BaseException:
            backup.rename(runtime)
            raise
        print('Previous runtime preserved at: '+str(backup))
    return runtime


def isolate_keychain(runtime):
    from patch_keychain_identity import identity, patch, SERVICE, LABEL
    runtime = Path(runtime).resolve()
    bundle = verify(runtime)
    if identity(bundle) == 'isolated':
        return runtime
    # Never edit an active executable in place: sign and verify a staged copy first.
    with tempfile.TemporaryDirectory(prefix='.tablecraft-keychain-', dir=runtime.parent) as temp:
        stage = Path(temp)/'runtime'
        subprocess.run(['/usr/bin/ditto', str(runtime), str(stage)], check=True)
        staged_bundle = stage/'TableCraft.app'
        changes = patch(staged_bundle)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                        '--preserve-metadata=entitlements', str(staged_bundle)], check=True)
        manifest = json.loads((stage/'manifest.json').read_text())
        manifest['entries'] = inventory(staged_bundle)
        manifest['overrides'] = overrides(staged_bundle)
        manifest['keychain'] = dict(service=SERVICE, label=LABEL, migrated_credentials=False,
                                    architectures=['arm64', 'x86_64'], changes=changes)
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
        verify(stage)
        backup_root = ROOT/'analysis/runtime-backups'
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='before-keychain-', dir=backup_root))/'runtime'
        runtime.rename(backup)
        try:
            stage.rename(runtime)
        except BaseException:
            backup.rename(runtime)
            raise
        print('Previous runtime preserved at: '+str(backup))
    return runtime


def package(output):
    verify(ROOT/'runtime')
    output = Path(output).resolve()
    if output.exists() or output.with_suffix(output.suffix + '.sha256').exists():
        raise ValueError('Output already exists; choose another --output path')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.tablecraft-package-', dir=output.parent) as temp:
        stage = Path(temp)/'TableCraft-portable'
        stage.mkdir()
        # Explicit allowlist: never copy profiles, connections, analysis or repository metadata.
        for folder, suffixes in {'scripts': {'.py', '.sh'}, 'assets/icons': {'.png', '.icns'},
                                 'docs': {'.md', '.sql'}}.items():
            target = stage/folder
            target.mkdir(parents=True)
            for source in (ROOT/folder).iterdir():
                if source.is_file() and source.suffix in suffixes and source.name not in {'reference-craft.png', 'macos-resolved-icon.png'}:
                    shutil.copy2(source, target/source.name)
        shutil.copytree(ROOT/'docs/images', stage/'docs/images')
        for name in ('Avvia TableCraft.command', 'README.md', 'README.en.md', 'NOTICE', 'LICENSE', 'CONTRIBUTING.md', 'CHANGELOG.md', 'requirements-analysis.txt'):
            shutil.copy2(ROOT/name, stage/name)
        subprocess.run(['/usr/bin/ditto', str(ROOT/'runtime'), str(stage/'runtime')], check=True)
        verify(stage/'runtime')
        archive = Path(temp)/'portable.zip'
        subprocess.run(['/usr/bin/ditto', '-c', '-k', '--keepParent', str(stage), str(archive)], check=True)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.rename(output)
        output.with_suffix(output.suffix+'.sha256').write_text(digest+'  '+output.name+'\n')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('embed', 'verify', 'package', 'isolate-keychain', 'rename-mcp', 'brand-mcp-settings', 'brand-mcp-registration', 'isolate-mcp'))
    parser.add_argument('--source', type=Path, default=ROOT/'analysis/copies/TablePlus-Research.app')
    parser.add_argument('--runtime', type=Path, default=ROOT/'runtime')
    parser.add_argument('--output', type=Path, default=ROOT/'dist/TableCraft-portable-macos-arm64.zip')
    args = parser.parse_args()
    try:
        if args.action == 'embed':
            print(embed(args.source, args.runtime))
        elif args.action == 'isolate-mcp':
            print(isolate_mcp(args.runtime))
        elif args.action == 'brand-mcp-registration':
            print(brand_mcp_registration(args.runtime))
        elif args.action == 'brand-mcp-settings':
            print(brand_mcp_settings(args.runtime))
        elif args.action == 'rename-mcp':
            print(rename_mcp(args.runtime))
        elif args.action == 'isolate-keychain':
            print(isolate_keychain(args.runtime))
        elif args.action == 'verify':
            print(verify(args.runtime))
        else:
            if args.runtime != ROOT/'runtime':
                parser.error('package uses the runtime embedded in this project')
            print(package(args.output))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, 'Portable runtime: {}\n'.format(error))


if __name__ == '__main__':
    main()
