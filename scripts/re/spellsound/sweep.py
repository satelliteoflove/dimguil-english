"""sweep.py OUT.jsonl PAR STATE[,STATE...] CADENCES OFFSETS: replay.py on both discs (ca912fe8
published, ba2a42a6 with the fix) for every state x cadence x offset, PAR at a time; one
JSON line per run appended to OUT.jsonl. Run from the worktree root."""
import sys, os, subprocess, itertools
from concurrent.futures import ThreadPoolExecutor
out, par = sys.argv[1], int(sys.argv[2])
states, cads, offs = sys.argv[3].split(','), sys.argv[4].split(','), sys.argv[5].split(',')
T = os.path.dirname(os.path.abspath(__file__))
D = 'rips/re/work/spellfix/discs'
def one(job):
    st, c, o, d = job
    r = subprocess.run(['python3', os.path.join(T, 'replay.py'), '%s/%s/dimguil-en.cue' % (D, d), st, c, o, '20000'],
                       capture_output=True, text=True)
    line = (r.stdout.strip().splitlines() or ['{"error": %r, "job": %r}' % (r.stderr[-300:], job)])[-1]
    with open(out, 'a') as f:
        f.write(line + '\n')
jobs = list(itertools.product(states, cads, offs, ('ca912fe8', 'ba2a42a6')))
with ThreadPoolExecutor(par) as ex:
    list(ex.map(one, jobs))
print('done', len(jobs))
