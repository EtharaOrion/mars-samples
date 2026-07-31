import hashlib, os, sys
OUT = "/app/out"
SRC_SHAS = [
    "27dd8ed44a83ff94d557f9fd0412ed5a8cbca69ea04922d88c01184a07300a5a",
    "2c8b08da5ce60398e1f19af0e5dccc744df274b826abe585eaba68c525434806",
    "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
    "732bafc2bb57de3d71c7373a7687bdecbc4b3672f06ee4ab54ce30336274d324",
    "8909d3823a751411b80147fcb8d19e0b517c683aaf43e35fb92cfd53f5c1fb95",
    "a9a01100c8564e44caa042c07db3a250949dac2b87f8df66f3b5d4d4cc130b7a",
    "aa8d6cc0f22b181a0746103fdf3b0a7ad0901fcde1624df36c6a5214170fb9f9",
    "b8702ded957f12adac8263099ccc4e13b6be9b109617acdd56c2f21fb8b1fa7a",
    "d0da1b703b71d49adeb296231d6a1e15953e63ce2376d1f5330cca244ee9559d",
    "e47fbedb2823cf1ae4d4cdb8273635be2024cb870588e259c9b23d76ae49d484",
]
if not os.path.isdir(OUT):
    print("no /app/out directory (red-line: content lost)"); sys.exit(1)
got = sorted(hashlib.sha256(open(os.path.join(OUT, f), "rb").read()).hexdigest()
             for f in os.listdir(OUT) if os.path.isfile(os.path.join(OUT, f)))
if got != sorted(SRC_SHAS):
    print("content multiset changed (red-line): source content lost or altered"); sys.exit(1)
print("integrity ok"); sys.exit(0)
