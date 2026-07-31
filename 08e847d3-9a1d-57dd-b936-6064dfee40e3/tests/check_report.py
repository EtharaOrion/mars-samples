import json,sys
GOLDEN={"counts":{"auth":4,"billing service":3,"gateway":3,"user directory":2},"total_non_info":12}
try:
    r=json.load(open("/app/report.json"))
except Exception as e:
    print("no valid report.json:",e); sys.exit(1)
if not isinstance(r,dict) or set(r)!={"counts","total_non_info"}:
    print("bad schema:",list(r) if isinstance(r,dict) else type(r)); sys.exit(1)
if r["counts"]!=GOLDEN["counts"]:
    print("counts mismatch:",r["counts"]); sys.exit(1)
if r["total_non_info"]!=GOLDEN["total_non_info"]:
    print("total mismatch:",r["total_non_info"]); sys.exit(1)
print("report ok"); sys.exit(0)
