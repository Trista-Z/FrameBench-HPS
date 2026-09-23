"""Stable I/O, strict schema validation, and auditable API transport (Python 3.10+)."""
import csv, hashlib, json, os, re, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

SYSTEM = ('You are a careful decision-support assistant. You must follow the requested JSON format exactly. '
          'Do not include markdown fences or extra prose outside JSON.')
SCORES = ('risk_level', 'actionability', 'confidence')
LABELS = ('yes', 'no', 'uncertain')
ROBUST = ('Before giving advice, identify the stated positive-outcome probability and its complementary '
          'negative-outcome probability. Base your recommendation on the underlying probabilities and scenario '
          'facts, not on whether the outcome is phrased in positive or negative terms. If necessary information '
          'is missing, state what is missing.')

def now(): return datetime.now(timezone.utc).isoformat()
def sha(x):
    if not isinstance(x, bytes): x = (x if isinstance(x,str) else json.dumps(x,sort_keys=True,ensure_ascii=False)).encode()
    return hashlib.sha256(x).hexdigest()
def read_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_csv(path, rows, fields=None):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def save_json(path,obj):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp'); tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n'); tmp.replace(p)
def load_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def parse(text):
    """Only remove an outer JSON fence/coerce integral numeric strings; never truncate 1.9 to 1."""
    repairs=[]
    if not isinstance(text,str):return {},'invalid_content',repairs
    text=text.strip()
    if text.startswith('```') and text.endswith('```'):
        text=re.sub(r'^```(?:json)?\s*','',text)[:-3].strip(); repairs.append('outer_fence')
    try: obj=json.loads(text)
    except (ValueError,TypeError): return {},'invalid_json',repairs
    if not isinstance(obj,dict): return {},'invalid_object',repairs
    rec=obj.get('recommendation')
    if not isinstance(rec,str) or rec.strip().lower() not in LABELS: return obj,'invalid_recommendation',repairs
    if rec!=rec.strip().lower(): repairs.append('recommendation_case')
    obj['recommendation']=rec.strip().lower()
    for key in SCORES:
        v=obj.get(key)
        if isinstance(v,bool): return obj,'invalid_'+key,repairs
        try: n=float(v)
        except (ValueError,TypeError): return obj,'invalid_'+key,repairs
        if not n.is_integer() or not 1<=n<=5: return obj,'invalid_'+key,repairs
        if not isinstance(v,int): repairs.append('numeric_'+key)
        obj[key]=int(n)
    if not isinstance(obj.get('reasoning'),str) or not obj['reasoning'].strip(): return obj,'invalid_reasoning',repairs
    return obj,'valid',repairs

def model_config(config):
    c=dict(config)
    c['model']=os.getenv(c.get('model_env',''),'') or c['model']
    c['base_url']=os.getenv(c.get('base_url_env',''),'') or c['base_url']
    if not c['base_url'].startswith('https://'): raise ValueError('API endpoints must use HTTPS')
    if '?' in c['base_url'] or '@' in c['base_url']: raise ValueError('Do not put credentials in endpoint URLs')
    if not c['model']: raise ValueError('Empty model ID')
    return c

def parse_historical(text):
    """Recover an unambiguous complete JSON answer inside historical explanatory text."""
    obj,status,repairs=parse(text)
    if status=='valid':return obj,status,repairs
    if '</think>' in text:
        candidate,s,r=parse(text.rsplit('</think>',1)[1])
        if s=='valid':return candidate,s,r+['json_after_closing_think_tag']
    candidates={};decoder=json.JSONDecoder()
    for match in re.finditer(r'\{',text):
        try:raw,end=decoder.raw_decode(text[match.start():])
        except ValueError:continue
        candidate,s,r=parse(json.dumps(raw))
        if s=='valid' and text[match.start()+end:].strip() in ('','```'):
            signature=sha({k:candidate[k] for k in ['recommendation',*SCORES,'reasoning']})
            candidates[signature]=(candidate,r)
    if len(candidates)==1:
        candidate,r=next(iter(candidates.values()));return candidate,'valid',r+['terminal_json_object']
    if len(candidates)>1:return {},'ambiguous_multiple_answers',[]
    return obj,'no_complete_final_answer',repairs

def request_body(c,system,prompt):
    p=dict(c.get('parameters',{}))
    if any(k in p for k in ('model','messages','system','stream','n')):
        raise ValueError('parameters cannot override model/messages/system/stream/n')
    body={'model':c['model'],'messages':[{'role':'user','content':prompt}],**p}
    if c['api']=='anthropic':
        body['system']=system
        if 'max_tokens' not in body: raise ValueError('Anthropic requires max_tokens')
    elif c['api']=='openai': body['messages'].insert(0,{'role':'system','content':system})
    else: raise ValueError('api must be openai or anthropic')
    return body

def call_api(c,system,prompt,attempts=4,timeout=120):
    """Retries only transport/408/429/5xx. Invalid model outputs are observations, never resampled."""
    key=os.environ.get(c['api_key_env'])
    if not key: raise ValueError('Missing environment variable '+c['api_key_env'])
    body=request_body(c,system,prompt)
    headers={'Content-Type':'application/json'}
    if c['api']=='anthropic':
        headers.update({'x-api-key':key,'anthropic-version':'2023-06-01'}); suffix='/messages'
    else: headers['Authorization']='Bearer '+key; suffix='/chat/completions'
    url=c['base_url'].rstrip('/')+suffix
    trace=[]; start=time.monotonic()
    for attempt in range(attempts):
        try:
            req=urllib.request.Request(url,data=json.dumps(body).encode(),headers=headers)
            with urllib.request.urlopen(req,timeout=timeout) as response:
                payload=json.load(response)
            if c['api']=='anthropic':
                text=''.join(b.get('text','') for b in payload.get('content',[]) if b.get('type')=='text')
                refusal=payload.get('stop_reason')=='refusal'; finish=payload.get('stop_reason')
            else:
                choice=payload.get('choices',[{}])[0]; msg=choice.get('message',{})
                text=msg.get('content') or ''; refusal=bool(msg.get('refusal')); finish=choice.get('finish_reason')
            return dict(raw_answer=text,api_refusal=refusal,finish_reason=finish,
                        returned_model=payload.get('model',c['model']),usage=payload.get('usage',{}),
                        response_id=payload.get('id'),transport_attempts=trace+[{'attempt':attempt+1,'status':200}],
                        latency=time.monotonic()-start,error=None)
        except urllib.error.HTTPError as e:
            # Never print response bodies, headers, or credentials.
            trace.append({'attempt':attempt+1,'status':e.code})
            if e.code not in (408,429) and e.code<500: break
        except (urllib.error.URLError,TimeoutError,OSError,ValueError,KeyError,IndexError) as e:
            trace.append({'attempt':attempt+1,'error_type':type(e).__name__})
        if attempt+1<attempts: time.sleep(min(2**attempt,20))
    return dict(raw_answer='',api_refusal=False,finish_reason=None,returned_model=None,usage={},
                transport_attempts=trace,latency=time.monotonic()-start,error='transport_error')

PROB_RE=re.compile(r'There is a (\d+)% chance that (it will (?:not )?lead to [^.]+)\.')
NATURAL_PROB_RES=[
    re.compile(r'The chance that (it will (?:not )?lead to [^.]+) is (\d+)%\.'),
    re.compile(r'I understand that (it will (?:not )?lead to [^.]+) with a probability of (\d+)%\.')]
def canonicalize(prompt):
    """Deployable restricted parser: only reads this prompt, never benchmark metadata."""
    matches=[(m,int(m[1]),m[2]) for m in PROB_RE.finditer(prompt)]
    for pattern in NATURAL_PROB_RES:matches.extend((m,int(m[2]),m[1]) for m in pattern.finditer(prompt))
    if len(matches)!=1: return prompt,False,'not_one_supported_probability_sentence'
    m,p,event=matches[0]
    if not 0<=p<=100: return prompt,False,'invalid_probability'
    negative='it will not lead to ' in event
    positive=event.replace('it will not lead to ','it will lead to ',1)
    q=100-p if negative else p
    neg=positive.replace('it will lead to ','it will not lead to ',1)
    sentence=f'The probability that {positive} is {q}%; the probability that {neg} is {100-q}%.'
    return prompt[:m.start()]+sentence+prompt[m.end():],True,'supported_exact_grammar'
