"""Consistent SQLite backup; destination must be a new private file."""
import argparse
import os
from pathlib import Path
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument('source')
parser.add_argument('destination')
args = parser.parse_args()
os.umask(0o077)
source = Path(args.source).resolve(strict=True)
destination = Path(args.destination)
with destination.open('xb'):
    pass
try:
    with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as original, sqlite3.connect(destination) as backup:
        original.backup(backup)
        if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('backup integrity check failed')
    print('Consistent backup verified')
except Exception:
    destination.unlink(missing_ok=True)
    raise
