"""Executor-only workflow: run the frozen API experiment and return raw results."""
import argparse, getpass, json, os, sqlite3, subprocess, sys
from pathlib import Path
from common import load_json, model_config, read_csv, save_json, now, sha

ROOT = Path(__file__).resolve().parent
DEV_REPEATS = 1
TEST_REPEATS = 3


def command(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)


def configs(path='configs/models.json'):
    return [model_config(c) for c in load_json(ROOT / path)['models']]


def ensure_keys(cfgs):
    for c in cfgs:
        env = c['api_key_env']
        if not os.getenv(env):
            value = getpass.getpass(f'{env} (hidden; not saved): ').strip()
            if not value:
                raise SystemExit('Missing ' + env)
            os.environ[env] = value


def rewrites_approved():
    """Minimal integrity check for the author-frozen rewrite file."""
    path = ROOT / 'work/rewrite_review.csv'
    if not path.exists():
        return False
    rows = read_csv(path)
    if len(rows) != 40:
        return False
    seen = set()
    for r in rows:
        key = (r.get('scenario_id'), r.get('style'))
        if key in seen:
            return False
        seen.add(key)
        context = r.get('context', '')
        if not (
            r.get('decision') == 'accept'
            and bool(r.get('reviewer_id'))
            and r.get('automatic_checks') == 'pass'
            and context.count('<PROBABILITY>') == 1
            and r.get('context_sha256') == sha(context)
        ):
            return False
    return True


def build_manifest(stage, block, repeats):
    path = ROOT / 'work' / f'{stage}_{block}.json'
    if path.exists():
        return path
    command('prepare.py', 'build', '--block', block, '--split', stage,
            '--repeats', repeats, '--output', path)
    return path


def run_block(stage, block, repeats, config, workers):
    manifest = build_manifest(stage, block, repeats)
    out = ROOT / 'runs' / f'{stage}_{block}'
    command('run.py', '--manifest', manifest, '--out', out, '--config', config,
            '--workers', workers, '--retry-errors')
    return out


def dev_invalid_gate(run_dirs):
    totals = {}
    for out in run_dirs:
        db = sqlite3.connect(out / 'results.sqlite')
        for (record,) in db.execute('SELECT record FROM results'):
            r = json.loads(record)
            key = r['model_alias']
            cur = totals.setdefault(key, [0, 0])
            cur[0] += 1
            cur[1] += r['validation_status'] != 'valid'
        db.close()
    bad = {
        k: {'invalid': v[1], 'total': v[0], 'rate': v[1] / v[0]}
        for k, v in totals.items() if v[0] and v[1] / v[0] > 0.10
    }
    if bad:
        out = ROOT / 'RETURN_TO_AUTHOR'
        out.mkdir(exist_ok=True)
        save_json(out / 'dev_gate_failure.json', {'timestamp': now(), 'bad': bad, 'all': totals})
        command('collect_results.py', '--partial')
        raise SystemExit(
            'Stopped after dev because >10% outputs were invalid for at least one model. '
            'Return RETURN_TO_AUTHOR/ to the author; do not change the protocol or models.'
        )


def main():
    ap = argparse.ArgumentParser(description='FrameBench revision executor-only API runner.')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--config', default='configs/models.json')
    args = ap.parse_args()
    if args.workers < 1:
        ap.error('--workers must be >= 1')
    os.chdir(ROOT)

    # Author-side rewrite review is already complete. We only verify the frozen file was not altered.
    if not rewrites_approved():
        raise SystemExit(
            'STOP: work/rewrite_review.csv is missing, incomplete, unapproved, or changed after approval. '
            'Expected 40 approved conversational rewrites with matching SHA-256 hashes. No API call was made.'
        )

    cfgs = configs(args.config)
    ensure_keys(cfgs)

    # No separate preflight and no rewrite-generation calls. Dev is the first real experiment block.
    dev = [run_block('dev', b, DEV_REPEATS, args.config, args.workers)
           for b in ('original', 'natural', 'mitigation')]
    dev_invalid_gate(dev)

    for b in ('original', 'natural', 'mitigation'):
        run_block('test', b, TEST_REPEATS, args.config, args.workers)

    command('collect_results.py')
    print('\nAPI work complete. Return RETURN_TO_AUTHOR_RESULTS.zip to the author.')


if __name__ == '__main__':
    main()
