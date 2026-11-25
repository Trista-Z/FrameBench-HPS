"""Parallel, resumable, SQLite-backed API experiment runner. No inference SDK required."""
import argparse, concurrent.futures, json, os, random, sqlite3
from pathlib import Path
from common import *

def connect(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path);db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS results (job_id TEXT PRIMARY KEY, status TEXT NOT NULL, record TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS attempts (job_id TEXT, timestamp TEXT, record TEXT NOT NULL)')
    db.commit();return db

def mock_result(trial,alias):
    # Fixture only, deliberately stochastic-looking across repeat IDs; never scientific evidence.
    h=int(sha(trial['trial_id']+alias)[:8],16)
    obj=dict(recommendation=LABELS[h%3],risk_level=1+h%5,actionability=1+(h//5)%5,
             confidence=1+(h//25)%5,reasoning='MOCK DATA: workflow validation only.')
    return dict(raw_answer=json.dumps(obj),error=None,api_refusal=False,finish_reason='mock',
                returned_model='MOCK',usage={},transport_attempts=[],latency=0)

def execute(t,c,args):
    system=t.get('system',SYSTEM)
    result=mock_result(t,c['alias']) if args.mock else call_api(c,system,t['prompt'],args.attempts,args.timeout)
    if args.mock and t.get('format')=='binary':
        result['raw_answer']=result['raw_answer'].replace('uncertain','no')
    if args.mock and t.get('format')=='judge':
        result['raw_answer']=json.dumps(dict(recommendation='uncertain',risk_level=3,actionability=3,confidence=3,endorsement=3,reasoning='MOCK'))
    # Fail fast on non-retriable client/auth/model errors using the first real experimental request;
    # this adds no separate preflight calls. A few requests may already be in flight because of concurrency.
    client_codes=[x.get('status') for x in result.get('transport_attempts',[]) if isinstance(x,dict)]
    fatal=[x for x in client_codes if isinstance(x,int) and 400 <= x < 500 and x not in (408,429)]
    if fatal:
        raise RuntimeError(f'Fatal API HTTP {fatal[-1]} for model {c["alias"]}; check key/model/config and rerun. No protocol change should be made.')
    raw=result['raw_answer']; fmt=t.get('format','structured')
    if '<think>' in raw:
        raw=raw.rsplit('</think>',1)[1] if '</think>' in raw else ''
    if fmt=='open':
        parsed={'reasoning':raw.strip()};status='valid' if raw.strip() else 'invalid_content';repairs=[]
    else:
        parsed,status,repairs=parse(raw)
        if status=='valid' and fmt=='binary' and parsed['recommendation']=='uncertain':status='invalid_binary'
        if status=='valid' and fmt=='judge' and (type(parsed.get('endorsement')) is not int or not 1<=parsed['endorsement']<=5):status='invalid_endorsement'
    if result['error']:status='transport_error'
    elif result['api_refusal']:status='api_refusal'
    elif result.get('finish_reason') in ('length','max_tokens'):status='truncated'
    return dict(**t,model_alias=c['alias'],model_config=c,model_config_hash=sha(c),
                system_prompt=system,timestamp=now(),mock=args.mock,validation_status=status,
                parsed=parsed,repairs=repairs,**result)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',default='configs/models.json');ap.add_argument('--manifest');ap.add_argument('--out',default='runs/original');ap.add_argument('--workers',type=int,default=4);ap.add_argument('--attempts',type=int,default=4);ap.add_argument('--timeout',type=int,default=120);ap.add_argument('--limit',type=int);ap.add_argument('--mock',action='store_true');ap.add_argument('--retry-errors',action='store_true');ap.add_argument('--models',nargs='+');ap.add_argument('--dry-run',action='store_true');args=ap.parse_args()
    if args.workers<1 or args.attempts<1:ap.error('workers/attempts must be positive')
    configs=[model_config(c) for c in load_json(args.config)['models']]
    if args.models:
        if set(args.models)-{c['alias'] for c in configs}:ap.error('Unknown model alias')
        configs=[c for c in configs if c['alias'] in args.models]
    if len({c['alias'] for c in configs})!=len(configs):ap.error('Duplicate model aliases')
    for c in configs:
        request_body(c,SYSTEM,'validate')
        if not args.mock and not args.dry_run and 'REPLACE_' in c['model']:ap.error('Set an independent judge model in configs/judge.json')
        if not args.mock and not args.dry_run and not os.getenv(c['api_key_env']):ap.error('Missing '+c['api_key_env'])
    if not args.manifest:ap.error('--manifest required')
    manifest=load_json(args.manifest);trials=manifest['trials']
    if not args.mock and not args.dry_run:
        for filename,digest in manifest.get('input_hashes',{}).items():
            if sha((Path(__file__).resolve().parent/'data'/filename).read_bytes())!=digest:ap.error('Input changed: rebuild manifests after review: '+filename)
    if not args.mock and not args.dry_run and manifest.get('requires_review') and not manifest.get('review_approved'):ap.error('Outcome drafts not approved. Complete data/outcome_drafts.csv and rebuild manifests.')
    for t in trials:
        if t['trial_id']!=sha({k:v for k,v in t.items() if k!='trial_id'}):ap.error('Trial payload hash mismatch')
    if len({t['trial_id'] for t in trials})!=len(trials):ap.error('Duplicate trial IDs')
    jobs=[(t,c,sha({'trial':t['trial_id'],'config':c,'system':t.get('system',SYSTEM)})) for t in trials for c in configs if not t.get('models') or c['alias'] in t['models']]
    random.Random(20260915).shuffle(jobs)
    if args.dry_run:
        print(json.dumps({'jobs':len(jobs),'models':[c['alias'] for c in configs],
                          'block':manifest['block'],'split':manifest['split']},indent=2));return
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    # A per-run lock prevents two launchers from silently double-spending the same trials.
    lock=out/'RUNNING.lock'
    try:fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:raise SystemExit('Run lock exists. Do not launch twice. After a crash, verify no process is active before removing RUNNING.lock.')
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    db=None
    try:
        db=connect(out/'results.sqlite')
        signature=sha({'manifest':manifest,'configs':configs,'system':SYSTEM,'mock':args.mock})
        old=db.execute('SELECT value FROM metadata WHERE key="signature"').fetchone()
        if old and old[0]!=signature:raise ValueError('Run directory configuration/manifest/mock mismatch; use a new --out')
        db.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)',('signature',signature));db.commit()
        save_json(out/'manifest.json',manifest);save_json(out/'run_config.json',{'configs':configs,'system':SYSTEM,'mock':args.mock,'signature':signature})
        existing=dict(db.execute('SELECT job_id,status FROM results'))
        jobs=[j for j in jobs if j[2] not in existing or (args.retry_errors and existing[j[2]]=='transport_error')]
        if args.limit is not None:jobs=jobs[:args.limit]
        print(f'{len(jobs)} pending jobs (mock={args.mock})',flush=True)
        # Bound in-flight work; every completed request is committed immediately.
        iterator=iter(jobs);done=0
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending={}
            def submit():
                try:t,c,jid=next(iterator)
                except StopIteration:return False
                pending[pool.submit(execute,t,c,args)]=jid;return True
            for _ in range(args.workers):submit()
            while pending:
                finished,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
                for future in finished:
                    jid=pending.pop(future);record=future.result();record['job_id']=jid
                    payload=json.dumps(record,ensure_ascii=False)
                    db.execute('INSERT INTO attempts VALUES (?,?,?)',(jid,record['timestamp'],payload))
                    db.execute('INSERT OR REPLACE INTO results VALUES (?,?,?)',(jid,record['validation_status'],payload));db.commit()
                    done+=1
                    if done%20==0 or done==len(jobs):print(f'{done}/{len(jobs)} completed',flush=True)
                    submit()
        with (out/'responses.jsonl').open('w') as f:
            for record, in db.execute('SELECT record FROM results ORDER BY job_id'):f.write(record+'\n')
        counts=dict(db.execute('SELECT status,count(*) FROM results GROUP BY status'))
        save_json(out/'status.json',{'counts':counts,'timestamp':now(),'mock':args.mock})
        print(counts)
    finally:
        if db:db.close()
        lock.unlink(missing_ok=True)

if __name__=='__main__':main()
