import hashlib, os, sys
OUT = "/app/out"
GOLDEN = {
    "a-b-c.md": "a9a01100c8564e44caa042c07db3a250949dac2b87f8df66f3b5d4d4cc130b7a",
    "a-b.txt": "d0da1b703b71d49adeb296231d6a1e15953e63ce2376d1f5330cca244ee9559d",
    "hello-world.txt": "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
    "note.txt": "b8702ded957f12adac8263099ccc4e13b6be9b109617acdd56c2f21fb8b1fa7a",
    "report-v1-1.txt": "27dd8ed44a83ff94d557f9fd0412ed5a8cbca69ea04922d88c01184a07300a5a",
    "report-v1.txt": "2c8b08da5ce60398e1f19af0e5dccc744df274b826abe585eaba68c525434806",
    "rf.txt": "732bafc2bb57de3d71c7373a7687bdecbc4b3672f06ee4ab54ce30336274d324",
    "spacey-file.log": "e47fbedb2823cf1ae4d4cdb8273635be2024cb870588e259c9b23d76ae49d484",
    "v.1.2-build.md": "8909d3823a751411b80147fcb8d19e0b517c683aaf43e35fb92cfd53f5c1fb95",
    "x-y.log": "aa8d6cc0f22b181a0746103fdf3b0a7ad0901fcde1624df36c6a5214170fb9f9",
}
if not os.path.isdir(OUT):
    print("no /app/out directory"); sys.exit(1)
have = set(os.listdir(OUT))
want = set(GOLDEN)
if have != want:
    print("filename set mismatch"); print("missing:", sorted(want - have)); print("extra:", sorted(have - want)); sys.exit(1)
for name, sha in sorted(GOLDEN.items()):
    got = hashlib.sha256(open(os.path.join(OUT, name), "rb").read()).hexdigest()
    if got != sha:
        print("content sha mismatch for", name, "got", got); sys.exit(1)
print("rename ok"); sys.exit(0)
