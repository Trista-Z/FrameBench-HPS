"""Collate raw API outputs for the author; performs no scientific analysis."""
import argparse, csv, json, sqlite3, zipfile, shutil
from pathlib import Path
from common import load_json, now, save_json

ROOT = Path(__file__).resolve().parent


def all_records():
    records=[]
    for run in sorted((ROOT/'runs').glob('*_*')):
        dbp=run/'results.sqlite'
        if not dbp.exists():
            continue
        db=sqlite3.connect(dbp)
        for (payload,) in db.execute('SELECT record FROM results ORDER BY job_id'):
            r=json.loads(payload);r['_run_dir']=run.name;records.append(r)
        db.close()
    return records


def flat(r):
    p=r.get('parsed') or {}
    c=r.get('model_config') or {}
    return {
        'run_dir': r.get('_run_dir'),
        'job_id': r.get('job_id'), 'trial_id': r.get('trial_id'),
        'split': r.get('split'), 'scenario_id': r.get('scenario_id'), 'domain': r.get('domain'),
        'probability_positive': r.get('probability_positive'), 'frame': r.get('frame'),
        'style': r.get('style'), 'intervention': r.get('intervention'), 'repeat_id': r.get('repeat_id'),
        'model_alias': r.get('model_alias'), 'requested_model': c.get('model'), 'returned_model': r.get('returned_model'),
        'validation_status': r.get('validation_status'), 'api_refusal': r.get('api_refusal'),
        'finish_reason': r.get('finish_reason'), 'recommendation': p.get('recommendation'),
        'risk_level': p.get('risk_level'), 'actionability': p.get('actionability'), 'confidence': p.get('confidence'),
        'reasoning': p.get('reasoning'), 'raw_answer': r.get('raw_answer'),
        'base_prompt': r.get('base_prompt'), 'prompt': r.get('prompt'),
        'timestamp': r.get('timestamp'), 'latency': r.get('latency'),
        'usage_json': json.dumps(r.get('usage',{}), ensure_ascii=False),
        'repairs_json': json.dumps(r.get('repairs',[]), ensure_ascii=False),
        'transport_attempts_json': json.dumps(r.get('transport_attempts',[]), ensure_ascii=False),
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');a=ap.parse_args()
    out=ROOT/'RETURN_TO_AUTHOR';out.mkdir(exist_ok=True)
    records=all_records()
    jsonl=out/('results_partial_raw.jsonl' if a.partial else 'results_raw.jsonl')
    with jsonl.open('w',encoding='utf-8') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    rows=[flat(r) for r in records]
    csvp=out/('results_partial_flat.csv' if a.partial else 'results_flat.csv')
    if rows:
        with csvp.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    statuses={}
    models={}
    for r in records:
        statuses[r.get('validation_status')]=statuses.get(r.get('validation_status'),0)+1
        key=(r.get('model_alias'),r.get('returned_model'))
        models[str(key)]=models.get(str(key),0)+1
    meta={'created_at':now(),'record_count':len(records),'status_counts':statuses,'returned_models':models,
          'note':'Operational collation only; no effect estimates or inferential statistics are computed here.'}
    save_json(out/('partial_metadata.json' if a.partial else 'run_metadata.json'),meta)
    for src,dst in [(ROOT/'work/split.json',out/'split.json'),(ROOT/'work/selected.csv',out/'selected.csv'),(ROOT/'work/rewrite_review.csv',out/'rewrite_review.csv')]:
        if src.exists():shutil.copy2(src,dst)
    if not a.partial:
        zip_path=ROOT/'RETURN_TO_AUTHOR_RESULTS.zip'
        with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(out.iterdir()):
                if p.is_file():z.write(p,p.name)
        print(f'Collated {len(records)} raw records -> {zip_path.name}')
    else:
        print(f'Collated {len(records)} partial raw records -> RETURN_TO_AUTHOR/')

if __name__=='__main__':main()
