import json,sys
GOLDEN={"features":{"beta":True,"cache":{"enabled":False,"ttl":120}},"logging":{"level":"warn","sinks":["stdout"]},"service":{"flags":["x","y","z"],"name":"api","port":9090,"workers":4}}
try:
    r=json.load(open("/app/merged.json"))
except Exception as e:
    print("no valid merged.json:",e); sys.exit(1)
if r!=GOLDEN:
    print("merge mismatch"); print("got:",json.dumps(r,sort_keys=True)); sys.exit(1)
print("merge ok"); sys.exit(0)
