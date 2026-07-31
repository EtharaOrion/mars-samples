import hashlib,os,sys
# True dependency graph (job -> jobs that must run before it)
TRUE_DEPS={
    "parse": [],
    "stats": ["parse"],
    "weights": ["parse"],
    "merge": ["stats","weights"],
    "report": ["merge"],
}
REDLINE_SHAS={
    "jobs/parse.sh": "403e1a94bb082b4ab198044437541b7ae7ea8941f85b82454fa0265ae7d4ce40",
    "jobs/stats.sh": "d475ee38df48917a9c7f5d0149abcefbcc75fa3681507c4fb8cf328f6b5b7508",
    "jobs/weights.sh": "fb582ca28de76a7a475ea2a944fb803562ed5d1ef2e9492cf6d5431c7b7f676a",
    "jobs/merge.sh": "052ca9810208d765d9ad482f6c454d13ed342b40266a912f2db01fe6826fd1f9",
    "jobs/report.sh": "5501684c46738c8386c582b76cfe8e5f11dc35040a73dd647d016461672ef2c0",
    "inputs/raw.txt": "5b67f73d292875520a23560cd3ede6ebef0f3b5ae9d1536e2bbaa290e6723f3a",
    "inputs/weights.txt": "1121cfccd5913f0a63fec40a6ffd44ea64f9dc135c66634ba001d10bcf4302a2",
    "inputs/base.txt": "eea8254c7500ba3de996aa8ad6af399183f04e17d4a8102fde539dbc93a90012",
}

def fail(msg):
    print(msg); sys.exit(1)

# --- RED LINE RL1: job definitions and inputs byte-identical ---
for rel,want in REDLINE_SHAS.items():
    p=os.path.join("/app",rel)
    if not os.path.isfile(p):
        fail("red-line file missing: "+rel)
    got=hashlib.sha256(open(p,"rb").read()).hexdigest()
    if got!=want:
        fail("red-line file modified: "+rel)
# name-set of jobs dir preserved (no added/removed job scripts)
jobset=set(f for f in os.listdir("/app/jobs") if f.endswith(".sh"))
expjobs=set(k.split("/")[1] for k in REDLINE_SHAS if k.startswith("jobs/"))
if jobset!=expjobs:
    fail("jobs dir set changed; got "+str(sorted(jobset)))
inset=set(os.listdir("/app/inputs"))
expin=set(k.split("/")[1] for k in REDLINE_SHAS if k.startswith("inputs/"))
if inset!=expin:
    fail("inputs dir set changed; got "+str(sorted(inset)))

# --- order.log is a valid topological order of TRUE_DEPS ---
P="/app/out/order.log"
if not os.path.isfile(P):
    fail("no /app/out/order.log")
seq=[l.strip() for l in open(P,encoding="utf-8").read().splitlines() if l.strip()]
if len(seq)!=len(TRUE_DEPS):
    fail("order.log length %d != %d; seq=%s"%(len(seq),len(TRUE_DEPS),seq))
if set(seq)!=set(TRUE_DEPS):
    fail("order.log job set mismatch; seq="+str(seq))
if len(set(seq))!=len(seq):
    fail("order.log has duplicate entries; seq="+str(seq))
pos={name:i for i,name in enumerate(seq)}
for job,deps in TRUE_DEPS.items():
    for d in deps:
        if pos[d]>=pos[job]:
            fail("dependency violated: '%s' must run before '%s'; seq=%s"%(d,job,seq))
print("order+integrity ok"); sys.exit(0)
