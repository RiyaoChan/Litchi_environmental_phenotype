from __future__ import annotations

import argparse
from .io_utils import freeze_inputs, load_config


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='V2 audit-first litchi experiment')
    parser.add_argument('stage', choices=['freeze', 'stage0', 'all'])
    parser.add_argument('--config', default='configs/base.yaml')
    args = parser.parse_args(argv)
    root, cfg = load_config(args.config)
    freeze_inputs(root, cfg)
    if args.stage == 'freeze':
        print('Frozen input manifest verified; raw files were not modified.')
        return 0
    from .pipeline import run
    return run(root, cfg, all_stages=args.stage == 'all')


if __name__ == '__main__':
    raise SystemExit(main())
