#!/usr/bin/env python3
"""Build claudcade.zip with all game files."""

import zipfile
from pathlib import Path


def build_claudcade():
    """Create claudcade.zip from game files."""
    root = Path(__file__).parent
    zip_path = root / 'claudcade-site' / 'public' / 'claudcade.zip'

    files_to_zip = [
        'claudcade.py',
        'claudcade_engine.py',
        'claudcade_scores.py',
        'ctype.py',
        'fight.py',
        'claudtra.py',
        'finalclaudesy.py',
        'superclaudio.py',
        'claudturismo.py',
        'claudemon.py',
        'launch_claudcade.sh',
        'launch_ctype.sh',
        'launch_fight.sh',
        'launch_claudtra.sh',
        'finalclaudesy/__init__.py',
        'finalclaudesy/ui.py',
        'finalclaudesy/main.py',
        'finalclaudesy/battle.py',
        'finalclaudesy/explore.py',
        'finalclaudesy/entities.py',
        'finalclaudesy/data.py',
    ]

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in files_to_zip:
            file_path = root / file
            if file_path.exists():
                arcname = Path(file).name if '/' not in file else file
                zf.write(file_path, arcname=arcname)
                print(f'Added {arcname}')

    print(f'\nBuilt {zip_path} ({zip_path.stat().st_size} bytes)')

if __name__ == '__main__':
    build_claudcade()
