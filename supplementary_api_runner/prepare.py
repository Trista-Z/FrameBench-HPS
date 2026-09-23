"""Construct frozen robustness/mitigation trial manifests from author-approved inputs."""
import argparse, random
from pathlib import Path
from common import *


def build(args):
    root = Path(args.work)
    rows = read_csv(root / 'selected.csv')
    reviews = {}
    if args.block != 'original':
        reviews = {(r['scenario_id'], r['style']): r for r in read_csv(root / 'rewrite_review.csv')}

    conditions = {
        'original': [('original', 'baseline')],
        'natural': [('conversational', 'baseline')],
        'mitigation': [
            ('conversational', 'canonicalization'),
            ('conversational', 'frame_robust_instruction'),
        ],
    }

    trials = []
    for r in rows:
        if r['split'] != args.split or r['frame'] not in ('gain', 'loss'):
            continue
        for style, method in conditions[args.block]:
            base = r['prompt']
            if style == 'conversational':
                q = reviews.get((r['scenario_id'], 'conversational'), {})
                if q.get('decision') != 'accept' or not q.get('reviewer_id') or q.get('automatic_checks') != 'pass':
                    raise ValueError(f'Rewrite approval missing: {r["scenario_id"]} conversational')
                context = q['context']
                if q.get('context_sha256') != sha(context):
                    raise ValueError('Edited rewrite needs refreshed hash and renewed human review')
                m = PROB_RE.search(base)
                if not m:
                    raise ValueError('Unsupported source probability sentence')
                instruction = base[base.index('\n\nPlease answer'):]
                probability_sentence = f'The chance that {m[2]} is {m[1]}%.'
                base = context.replace('<PROBABILITY>', probability_sentence) + instruction

            prompt = base
            supported = None
            reason = None
            if method == 'frame_robust_instruction':
                prompt = ROBUST + '\n\n' + base
            elif method == 'canonicalization':
                prompt, supported, reason = canonicalize(base)
                if not supported:
                    raise ValueError('Canonicalization unsupported: ' + str(reason))

            for rep in range(args.repeats):
                meta = {k: r[k] for k in ['scenario_id', 'domain', 'split', 'probability_positive', 'frame']}
                meta.update(
                    style=style,
                    intervention=method,
                    repeat_id=rep,
                    planned_repeats=args.repeats,
                    schema_version='revision_v3_executor_only',
                    base_prompt=base,
                    prompt=prompt,
                    canonical_supported=supported,
                    canonical_reason=reason,
                )
                meta['trial_id'] = sha(meta)
                trials.append(meta)

    random.Random(args.seed).shuffle(trials)
    p = Path(args.output)
    if p.exists():
        raise ValueError('Manifest exists; do not overwrite frozen trials')
    save_json(p, {
        'created_at': now(),
        'split_sha256': sha((root / 'split.json').read_bytes()),
        'repeats': args.repeats,
        'block': args.block,
        'split': args.split,
        'trials': trials,
    })
    print(f'{len(trials)} trials per model; {len(trials) * 3} API jobs with 3 models')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['build'])
    ap.add_argument('--work', default='work')
    ap.add_argument('--block', choices=['original', 'natural', 'mitigation'], required=True)
    ap.add_argument('--split', choices=['dev', 'test'], required=True)
    ap.add_argument('--repeats', type=int, required=True)
    ap.add_argument('--seed', type=int, default=20260915)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    if args.repeats < 1:
        ap.error('--repeats must be at least 1')
    build(args)
