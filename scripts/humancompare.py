#!/usr/bin/env python3
"""Print a humanwatch log as one line per fight, camp, chest and trip, from frame LO on:
    humancompare.py LOG.jsonl [LO]"""
import json,sys
def summ(path,lo=0,hi=1e12):
    L=[json.loads(l) for l in open(path)]
    out=[]
    for e in L:
        if not(lo<=e[0]<=hi): continue
        k=e[1]; d=e[2] if len(e)>2 else {}
        if k=='fought':
            hs=sum(x[1] for x in d['hp_start']); he=sum(x[1] for x in d['hp_end'])
            out.append('%d FIGHT a%s %s r%d %s fixed=%s hp %d->%d casts=%s mcasts=%s items=%s dead=%s status=%s gold=%s exp=%s new=%s fled=%s'%(e[0],d['where'][:3],[(g['name'].replace('\n',' '),g['n'],g['level']) for g in d['groups']],d['rounds'],d['outcome'],d.get('fixed'),hs,he,[c[1] for c in d['casts']],[c[1] for c in d['monster_casts']],[i[1] for i in d['items']],d['dead_end'],d['status_end'],d.get('gold'),d.get('exp'),d.get('items_new'),d.get('fled')))
        elif k=='camp':
            out.append('%d CAMP a%s spent=%s changes=%s'%(e[0],d['where'][:3],d['spent'],[c for c in d['changes']][:6]))
        elif k=='chest':
            out.append('%d CHEST %s'%(e[0],json.dumps(d)[:300]))
        elif k=='floor':
            out.append('%d FLOOR %s'%(e[0],d))
        elif k in('death','status','level'):
            out.append('%d %s %s'%(e[0],k.upper(),d))
        elif k in ('set out','home'):
            out.append('%d %s'%(e[0],k.upper()))
        elif k=='trip':
            out.append('%d TRIP %s'%(e[0],json.dumps(d)[:1500]))
    return out
p=sys.argv[1]; lo=float(sys.argv[2]) if len(sys.argv)>2 else 0
print('\n'.join(summ(p,lo)))
