"""Executor only: reconstruct the frozen prompts, run dev/test, export raw records."""
import argparse, collections, getpass, random, sqlite3, subprocess, sys, zipfile
from common import *
ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
THREE = ['openai','claude','gemini']
FOUR = ['gpt41mini','gpt5','gemini3flash','qwen']
OPEN_SYSTEM = 'You are a careful decision-support assistant. Give advice in natural language.'
BLOCKS = {'e1':(768,9216), 'e2':(256,3072), 'e2_all':(448,5376), 'e3_minimal':(288,3456), 'e3_all':(576,6912)}

def build(block, split, review_files=(), mock=False):
    rows=read_csv(DATA/'selected.csv'); rew={r['scenario_id']:r for r in read_csv(DATA/'rewrite_review.csv')}
    targets={r['scenario_id']:r['target'] for r in read_csv(DATA/'outcomes.csv')}
    mapping=load_json(DATA/'split.json')['mapping']
    if len(rows)!=480 or len(rew)!=40 or set(targets)!=set(mapping) or set(rew)!=set(mapping): raise ValueError('Input coverage mismatch')
    if any(r['split']!=mapping[r['scenario_id']] for r in rows): raise ValueError('Split mismatch')
    contexts={r['scenario_id']:r['scenario']+' My outcome target is '+targets[r['scenario_id']]+'. Meeting the target means achieving it; missing the target means any outcome in which it is not achieved.' for r in rows}
    approved=False
    if block=='e1' and review_files:
        if len(review_files)!=2: raise ValueError('Two independent H1 review CSVs required')
        reviews=[]
        for path in review_files:
            rr=read_csv(path); d={r['scenario_id']:r for r in rr}
            if len(rr)!=40 or set(d)!=set(targets): raise ValueError('Review coverage mismatch')
            for sid,v in d.items():
                if v['target']!=targets[sid] or v['context']!=contexts[sid] or v['decision'].strip().lower()!='accept' or not v['reviewer_id'].strip(): raise ValueError('Missing or stale H1 approval: '+sid)
            reviews.append(d)
        if any(reviews[0][s]['reviewer_id'].strip()==reviews[1][s]['reviewer_id'].strip() for s in targets): raise ValueError('H1 reviewers must be independent')
        approved=True
    trials=[]
    def add(experiment,r,condition,prompt,fmt,models,**extra):
        for j in range(1 if split=='dev' else 3):
            t={k:r[k] for k in ['scenario_id','domain','split','probability_positive','frame']}
            t.update(experiment=experiment,condition=condition,prompt=prompt,format=fmt,models=models,repeat_id=j,system=OPEN_SYSTEM if fmt=='open' else SYSTEM,**extra)
            t['trial_id']=sha(t);trials.append(t)
    for r in rows:
        if r['split']!=split or r['frame'] not in ('gain','loss'):continue
        sid=r['scenario_id']; p=int(r['probability_positive']); f=r['frame']; q=p if f=='gain' else 100-p
        suffix=r['prompt'][r['prompt'].index('\n\nPlease answer'):]
        if block=='e1':
            verbs={'affirmative':'meeting','negated':'not missing'} if f=='gain' else {'affirmative':'missing','negated':'not meeting'}
            context=contexts[sid]
            for neg,verb in verbs.items():
                question=f'{context} There is a {q}% chance of {verb} the target. What should I do?'
                for fmt in ('structured','open'):
                    add('e1',r,f+'_'+neg+'_'+fmt,question+(suffix if fmt=='structured' else '\nPlease explain your recommendation.'),fmt,THREE,negation=neg,judge_context=f'{context} Probability of meeting the target: {p}%; probability of missing the target: {100-p}%.'.replace('missing the target:','missing it:'))
        elif block.startswith('e2'):
            add('e2',r,f,r['prompt'],'structured',FOUR)
            if block=='e2_all': add('e2_controls',r,f,r['prompt'],'structured',THREE)
        else:
            review=rew[sid]; m=PROB_RE.search(r['prompt'])
            if not m or review['decision']!='accept' or review['automatic_checks']!='pass' or not review['reviewer_id'] or review['context_sha256']!=sha(review['context']): raise ValueError('Invalid conversational rewrite '+sid)
            conv=review['context'].replace('<PROBABILITY>',f'The chance that {m[2]} is {m[1]}%.')+suffix
            canon,ok,_=canonicalize(conv)
            if not ok: raise ValueError('Canonicalization failed '+sid)
            binary=conv.replace('"yes/no/uncertain"','"yes/no"')+'\nSelect either yes or no based on the available information. You may explain uncertainty in your reasoning.'
            add('e3_binary',r,f,binary,'binary',THREE)
            if block=='e3_all': add('e3_controls',r,'ternary_'+f,conv,'structured',THREE)
            if f=='gain':
                match=re.search(r'(The probability that [^;]+? is \d+%); the probability that ([^.]+? is \d+%)\.',canon)
                if not match: raise ValueError('Order swap failed '+sid)
                swapped=canon[:match.start()]+'The probability that '+match[2]+'; '+match[1][0].lower()+match[1][1:]+'.'+canon[match.end():]
                add('e3_order',r,'negative_first',swapped,'structured',THREE)
                if block=='e3_all': add('e3_controls',r,'positive_first',canon,'structured',THREE)
    # Match original per-block ordering-independent trial hashes; shuffle for execution.
    random.Random(20261125).shuffle(trials)
    n=sum(len(t['models']) for t in trials)
    if n!=BLOCKS[block][split=='test']: raise ValueError(f'Unexpected job count: {n}')
    return dict(block=block,split=split,trials=trials,requires_review=block=='e1',review_approved=approved if block=='e1' else True,input_hashes={f:sha((DATA/f).read_bytes()) for f in ['selected.csv','rewrite_review.csv','split.json','outcomes.csv']})

def export(root):
    output=ROOT/('MOCK_RESULTS.zip' if root.name.startswith('mock_') else 'REVISION_RESULTS.zip')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for db in sorted(root.glob('*/results.sqlite')):
            folder=db.parent; prefix='runs/'+root.name+'/'+folder.name+'/'
            with sqlite3.connect(db) as con:
                records=con.execute('SELECT record FROM results ORDER BY job_id')
                with z.open(prefix+'responses.jsonl','w') as f:
                    for (record,) in records:f.write((record+'\n').encode())
            for name in ('manifest.json','run_config.json','status.json'):
                if (folder/name).exists():z.write(folder/name,prefix+name)
    print('Send privately to author:',output.name)

def main():
    p=argparse.ArgumentParser();p.add_argument('block',nargs='?',choices=BLOCKS);p.add_argument('--workers',type=int,default=3);p.add_argument('--review',nargs=2,metavar=('CODER1','CODER2'));p.add_argument('--dev-only',action='store_true');p.add_argument('--dry-run',action='store_true');p.add_argument('--mock',action='store_true');p.add_argument('--retry-errors',action='store_true');p.add_argument('--cohort',default='revision_v1');p.add_argument('--export-only',action='store_true');a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.cohort):p.error('Invalid cohort name')
    root=ROOT/'runs'/(('mock_' if a.mock else '')+a.cohort)
    if a.export_only:
        if not list(root.glob('*/results.sqlite')):p.error('No saved results')
        export(root);return
    if not a.block:p.error('Choose e2_all, e3_all or e1 (see README)')
    if a.workers<1:p.error('workers must be positive')
    manifests={s:build(a.block,s,a.review or (),a.mock) for s in ('dev','test')}
    for s,m in manifests.items():print(s,sum(len(t['models']) for t in m['trials']),'calls')
    if a.dry_run:return
    if a.block=='e1' and not a.mock and not manifests['dev']['review_approved']:p.error('E1 requires --review CODER1.csv CODER2.csv')
    aliases={x for m in manifests.values() for t in m['trials'] for x in t['models']}
    configs=[c for c in load_json(ROOT/'models.json')['models'] if c['alias'] in aliases]
    if {c['alias'] for c in configs}!=aliases:p.error('Missing model configurations')
    if not a.mock:
        if 'qwen' in aliases and not os.getenv('QWEN_BASE_URL') and next(c for c in configs if c['alias']=='qwen')['base_url']=='https://localhost:8000/v1':os.environ['QWEN_BASE_URL']=input('Qwen API base URL (include /v1): ').strip()
        if 'qwen' in aliases and not os.getenv('QWEN_BASE_URL') and next(c for c in configs if c['alias']=='qwen')['base_url']=='https://localhost:8000/v1':p.error('Set QWEN_BASE_URL')
        for env in sorted({c['api_key_env'] for c in configs}):
            if not os.getenv(env):os.environ[env]=getpass.getpass(env+': ')
            if not os.getenv(env):p.error('Missing '+env)
    root.mkdir(parents=True,exist_ok=True)
    # Prevent accidental use of both the full and reduced budget variants in one cohort.
    other={'e2':'e2_all','e2_all':'e2','e3_minimal':'e3_all','e3_all':'e3_minimal'}.get(a.block)
    if other and (root/(other+'_dev')/'results.sqlite').exists():p.error('Other budget variant already started in this cohort')
    config=root/(a.block+'_config.json');save_json(config,{'models':configs})
    try:
        for split in ('dev','test'):
            manifest=root/(a.block+'_'+split+'.json');out=root/(a.block+'_'+split)
            save_json(manifest,manifests[split])
            cmd=[sys.executable,str(ROOT/'run.py'),'--config',str(config),'--manifest',str(manifest),'--out',str(out),'--workers',str(1 if split=='dev' else a.workers)]
            if a.mock:cmd.append('--mock')
            if a.retry_errors:cmd.append('--retry-errors')
            subprocess.run(cmd,check=True,cwd=ROOT)
            if split=='dev':
                expected=collections.Counter(m for t in manifests[split]['trials'] for m in t['models']); seen=collections.Counter(); bad=collections.Counter()
                for line in (out/'responses.jsonl').read_text().splitlines():
                    r=json.loads(line);m=r['model_alias'];seen[m]+=1;bad[m]+=r['validation_status']!='valid'
                for m,n in expected.items():
                    print(m,'invalid',bad[m],'/',n)
                    if seen[m]!=n or bad[m]/n>0.1:raise SystemExit('Dev gate failed; send raw results to author before changing anything')
                if a.dev_only:break
    finally:
        if list(root.glob('*/results.sqlite')):export(root)
if __name__=='__main__':main()
