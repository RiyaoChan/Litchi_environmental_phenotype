from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

DIRECTORIES = [
    'data/interim/documents', 'data/processed', 'data/metadata',
    'results/inventory', 'results/qc', 'results/descriptive',
    'results/phenology', 'results/windows', 'results/yield',
    'results/typhoon_case', 'results/scenarios', 'results/figures',
    'results/tables', 'results/logs', 'reports',
]


def load_config(path: str | Path) -> tuple[Path, dict]:
    path = Path(path).resolve()
    root = path.parent.parent
    return root, yaml.safe_load(path.read_text(encoding='utf-8'))


def prepare_dirs(root: Path) -> None:
    for name in DIRECTORIES:
        (root / name).mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               allow_nan=False) + '\n', encoding='utf-8')


def write_csv(path: Path, value, columns=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = value if isinstance(value, pd.DataFrame) else pd.DataFrame(value, columns=columns)
    df.to_csv(path, index=False, encoding='utf-8-sig', na_rep='NA',
              lineterminator='\n', float_format='%.10g')


def raw_paths(root: Path, cfg: dict) -> list[Path]:
    inputs = cfg['inputs']
    paths = [root / inputs['phenology'], root / inputs['yield']]
    paths += list((root / inputs['weather_dir']).glob('*.xlsx'))
    paths += list((root / inputs['documents_dir']).glob('*.doc'))
    if inputs.get('root_documents'):
        paths += list(root.glob('*.doc'))
    return sorted((p for p in paths if not p.name.startswith('~$')),
                  key=lambda p: p.relative_to(root).as_posix())


def inventory(root: Path, cfg: dict) -> list[dict]:
    return [dict(source_file=p.relative_to(root).as_posix(),
                 size_bytes=p.stat().st_size, sha256=sha256(p))
            for p in raw_paths(root, cfg)]


def freeze_inputs(root: Path, cfg: dict) -> list[dict]:
    """Create the baseline once. Never silently re-freeze changed inputs."""
    prepare_dirs(root)
    path = root / 'data/metadata/input_hashes.json'
    current = inventory(root, cfg)
    if path.exists():
        assert_inputs_unchanged(root, cfg)
    else:
        write_json(path, current)
    return current


def assert_inputs_unchanged(root: Path, cfg: dict) -> None:
    baseline = json.loads((root / 'data/metadata/input_hashes.json').read_text(encoding='utf-8'))
    if inventory(root, cfg) != baseline:
        raise RuntimeError('Raw inputs differ from the frozen baseline. Review and explicitly version a new input snapshot; no automatic overwrite.')


def season_bound(template: str, year: int):
    return pd.Timestamp(template.replace('{Y-1}', str(year - 1)).replace('{Y}', str(year)))
