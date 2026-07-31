import sys


def banned_token():
    # Assembled from parts so this scanner's own source does not contain the
    # literal token and therefore never trips on itself when it is linted.
    return "TODO_FIXME" + "_BANNED"


def scan(path, token):
    hits = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                if token in line:
                    hits.append(lineno)
    except OSError as exc:
        print("lint-error: cannot read %s: %s" % (path, exc))
        return None
    return hits


def main(argv):
    token = banned_token()
    failed = False
    for path in argv[1:]:
        hits = scan(path, token)
        if hits is None:
            failed = True
            continue
        for lineno in hits:
            print("FORBIDDEN: %s in %s:%d" % (token, path, lineno))
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
