import hashlib,sys
EXPECTED={
    "config/00-base.json": "055daba76b7cce73c200156c3beb3de00127f7e3020797f50c20315ffa5d5966",
    "config/10-env.json": "f8a3e7e414d877f3a24980c747808a092025cd67e7d6d82494fe6a2d389f9645",
    "config/20-override.json": "5bef7d4d0de4559b66525ec6ed5af2599361d893d79a1a430763bfa2a6398ad9",
}
bad=[r for r,w in EXPECTED.items() if hashlib.sha256(open("/app/"+r,"rb").read()).hexdigest()!=w]
if bad: print("source config modified (red-line):",bad); sys.exit(1)
print("integrity ok"); sys.exit(0)
