import hashlib

DATA = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]


def main():
    total = sum(DATA)
    payload = "widgetapp:v1:" + ",".join(str(x) for x in DATA)
    checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    print("widgetapp v1 ready sum=%d checksum=%s" % (total, checksum))


if __name__ == "__main__":
    main()
