import hashlib,os,sys
SOURCE_SHAS={
    "a_utf8_lf.txt": "cf84c1d5a30a849c20c6c1a7f48916844a4881a919fdbe29496db61b534eb773",
    "b_utf8_bom.txt": "bf3a1acc11a419f3a003079475b9042f68fe0ccab6d452f7cca8363371421b53",
    "c_latin1_crlf.txt": "f95b4cfb3ad3545479fae6862d50fb6b995f09a1cb25aa601b0cfa551dbbcdf1",
    "d_latin1_cr.txt": "5b05292a441bb1f64c799fa0fad62711675c934264830f475a6528b2cf3c20bc",
    "e_mixed_latin1.txt": "61b6d772b0a8d5cef362447a48bfcf6f837211857bfd4bfe5e7af745f6837b12",
    "f_utf8_crlf.txt": "ae439429d7ae5959355e6aa17a4d64d17ed0eac8f157e428c43fc85e3d689b04",
}
D="/app/corpus"
names=set(os.listdir(D))
expected=set(SOURCE_SHAS)
if names!=expected:
    print("source corpus set changed (red-line); missing=",sorted(expected-names),"extra=",sorted(names-expected)); sys.exit(1)
bad=[n for n,w in SOURCE_SHAS.items() if hashlib.sha256(open(os.path.join(D,n),"rb").read()).hexdigest()!=w]
if bad:
    print("source corpus modified (red-line):",bad); sys.exit(1)
print("integrity ok"); sys.exit(0)
