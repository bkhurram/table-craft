#!/usr/bin/env python3
"""Keep the user profile independent of the checkout; copy, never merge or delete."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def profile_path():
    override = os.environ.get('TABLECRAFT_PROFILE')
    if override and not Path(override).is_absolute():
        raise ValueError('TABLECRAFT_PROFILE must be an absolute path')
    return Path(override) if override else Path.home()/'Library/Application Support/TableCraft/runtime-profile'


def prepare_profile(destination, legacy):
    destination, legacy = Path(destination), Path(legacy)
    if destination.exists():
        if not destination.is_dir():
            raise ValueError('Profile path is not a directory')
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = destination.parent / ('.' + destination.name + '.migration-lock')
    lock.mkdir(mode=0o700)  # Fail closed on concurrent migration, including stale locks.
    try:
        if destination.exists():
            return destination
        with tempfile.TemporaryDirectory(prefix='.profile-migration-', dir=destination.parent) as temp:
            stage = Path(temp)/'profile'
            if legacy.is_dir():
                shutil.copytree(legacy, stage, symlinks=True)
            else:
                stage.mkdir(mode=0o700)
            stage.chmod(0o700)
            stage.rename(destination)
    finally:
        lock.rmdir()
    return destination


def snapshot_profile(profile):
    profile = Path(profile)
    backup_root = profile.parent/'profile-backups'
    backup_root.mkdir(exist_ok=True, mode=0o700)
    folder = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=backup_root))
    try:
        shutil.copytree(profile, folder/'runtime-profile', symlinks=True)
    except BaseException:
        shutil.rmtree(folder)
        raise
    return folder/'runtime-profile'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'snapshot', 'path'))
    args = parser.parse_args()
    profile = profile_path()
    if args.action != 'path':
        prepare_profile(profile, ROOT/'analysis/runtime-profile')
    if args.action == 'snapshot':
        print(snapshot_profile(profile))
    else:
        print(profile)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit('Profile operation failed: {}'.format(error))
