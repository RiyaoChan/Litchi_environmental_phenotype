"""Extract legacy .doc sources through a separate, hidden, read-only Word instance.

Use only for cache refresh; cached extracts are keyed by source SHA-256.
No Save, SaveAs or document conversion is performed.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.io_utils import load_config, freeze_inputs, assert_inputs_unchanged, raw_paths, sha256, write_json


def extract(root, cfg):
    import win32com.client
    sources = [p for p in raw_paths(root, cfg) if p.suffix == '.doc']
    pending = []
    for path in sources:
        target = root / 'data/interim/documents' / (sha256(path) + '.json')
        if not target.exists():
            pending.append((path, target))
    if not pending:
        print('All Word source caches are current.')
        return
    app = win32com.client.DispatchEx('Word.Application')
    app.Visible = False
    app.DisplayAlerts = 0
    app.AutomationSecurity = 3
    try:
        for path, target in pending:
            if target.exists():  # identical root/subdirectory duplicate
                continue
            doc = app.Documents.Open(str(path), ConfirmConversions=False,
                                     ReadOnly=True, AddToRecentFiles=False,
                                     Visible=False)
            try:
                text = doc.Content.Text.replace('\r', '\n')
                tables = []
                for i in range(1, doc.Tables.Count + 1):
                    cells = []
                    for cell in doc.Tables(i).Range.Cells:
                        cells.append({'row': int(cell.RowIndex),
                                      'column': int(cell.ColumnIndex),
                                      'text': cell.Range.Text.replace('\r\x07', '').replace('\r', '\n')})
                    tables.append({'table_index': i, 'cells': cells})
                write_json(target, {'source_sha256': sha256(path),
                                    'extraction_method': 'Word COM read-only',
                                    'text': text, 'tables': tables})
                print(f'Extracted {path.name}: {len(text)} characters, {len(tables)} tables', flush=True)
            finally:
                doc.Close(SaveChanges=0)
    finally:
        app.Quit(SaveChanges=0)
        assert_inputs_unchanged(root, cfg)


if __name__ == '__main__':
    root, cfg = load_config('configs/base.yaml')
    freeze_inputs(root, cfg)
    extract(root, cfg)
