import hashlib,os,sys
GOLDEN_SHAS={
    "a_utf8_lf.txt": "cf84c1d5a30a849c20c6c1a7f48916844a4881a919fdbe29496db61b534eb773",
    "b_utf8_bom.txt": "f478a0749a574e262ab673368e65cbc02730ce19630f18310a0d90b464c779fc",
    "c_latin1_crlf.txt": "b5e433a3849f2bf9560595dca7341c7bca95340af5374efe22337ac33ddbc7e7",
    "d_latin1_cr.txt": "8e26b4f0947444da726cf1570702aaa4b191b93e39a19e6d1467140a006d2bfc",
    "e_mixed_latin1.txt": "96c48094458a38fc88f044974c965169bf2206c9c3197ee7922e9866246bff1a",
    "f_utf8_crlf.txt": "e11311a72bb384d0daa0d745bdcbacd9d5516384529a9c33d7b2ad19760321aa",
}
D="/app/normalized"
if not os.path.isdir(D):
    print("no /app/normalized directory"); sys.exit(1)
names=set(os.listdir(D))
expected=set(GOLDEN_SHAS)
if names!=expected:
    print("normalized set mismatch; missing=",sorted(expected-names),"extra=",sorted(names-expected)); sys.exit(1)
bad=[]
for n,w in GOLDEN_SHAS.items():
    got=hashlib.sha256(open(os.path.join(D,n),"rb").read()).hexdigest()
    if got!=w: bad.append(n)
if bad:
    print("normalized bytes mismatch:",bad); sys.exit(1)
print("normalized ok"); sys.exit(0)
