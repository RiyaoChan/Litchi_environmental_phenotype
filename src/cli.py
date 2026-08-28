from __future__ import annotations

import argparse
from .io_utils import freeze_inputs, load_config


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Audit-first litchi experiments: legacy R2 and isolated R4 V3')
    parser.add_argument('stage', choices=['freeze', 'stage0', 'all','r4-qc','r4-describe','r4-p1','r4-p2','r4-p3','r4-windows','r4-yield','r4-scenarios','r4-all'])
    parser.add_argument('--config', default='configs/base.yaml')
    args = parser.parse_args(argv)
    root, cfg = load_config(args.config)
    if args.stage.startswith('r4-'):
        from .r4_pipeline import run_r4
        return run_r4(root,cfg,args.stage)
    freeze_inputs(root, cfg)
    if args.stage == 'freeze':
        print('Frozen input manifest verified; raw files were not modified.')
        return 0
    from .pipeline import run
    return run(root, cfg, all_stages=args.stage == 'all')


if __name__ == '__main__':
    raise SystemExit(main())
