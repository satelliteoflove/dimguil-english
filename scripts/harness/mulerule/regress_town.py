"""The suite's town-visit stuck cases, run with regress.run_case in this process, their
checkpoints redirected to rips/harness/mulerule/ (never regress/scratch).
usage: regress_town.py CASE_ID"""
import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness import regress, chapter1, chapters
cid = sys.argv[1]
case = next(json.loads(l) for l in open(regress.CASES) if json.loads(l)['id'] == cid)
for cls in (chapter1.Run, chapters.Run):
    orig = cls.__init__
    def init(self, *a, _orig=orig, **k):
        k['out'] = 'mulerule/regress_%d' % os.getpid()
        _orig(self, *a, **k)
    cls.__init__ = init
log = []
orig_upkeep = chapter1.town_upkeep
def upkeep(g, lg):
    orig_upkeep(g, lg)
    log.extend(x for x in lg if x[1] in ('backups', 'backup put', 'backup take', 'equip edge', 'mule made', 'backup stuck', 'sell'))
chapter1.town_upkeep = upkeep
rec = regress.run_case(case)
print(json.dumps(rec, default=str))
for x in log[-30:]:
    print('  ', json.dumps(x, default=str)[:300])
