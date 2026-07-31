import hashlib,sys
EXPECTED={
    "logs/app1.log": "c83e354eac70714ba0ea2b9d2a7d3504d97ed9262ec6d131872e89c0158dccd3",
    "logs/app2.log": "14101423a68b24bcc0b9db10d1c0b6467658dde111f8ed249e904aaaaf3aac89",
    "logs/app3.log": "0d531b477dcdc25f183b31c5e14a6f3ec0552f01f6574c8c90624b8deb82b743",
}
bad=[]
for rel,want in EXPECTED.items():
    try:
        got=hashlib.sha256(open("/app/"+rel,"rb").read()).hexdigest()
    except Exception as e:
        print("missing source:",rel,e); sys.exit(1)
    if got!=want: bad.append(rel)
if bad:
    print("source logs modified (red-line):",bad); sys.exit(1)
print("integrity ok"); sys.exit(0)
