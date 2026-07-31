import hashlib,os,sys
GOLDEN_RESULT_SHA="c5affdfa2da318d650095e2fbe99b6fdce629adb4f14647eae2c5001cc7e3eca"
P="/app/out/result.txt"
if not os.path.isfile(P):
    print("no /app/out/result.txt"); sys.exit(1)
got=hashlib.sha256(open(P,"rb").read()).hexdigest()
if got!=GOLDEN_RESULT_SHA:
    print("result.txt bytes mismatch; got sha",got); 
    print("---content---"); sys.stdout.write(open(P,encoding="utf-8",errors="replace").read())
    sys.exit(1)
print("result ok"); sys.exit(0)
