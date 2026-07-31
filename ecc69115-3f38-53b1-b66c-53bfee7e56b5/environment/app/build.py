#!/usr/bin/env python3
"""Offline monorepo build-graph runner (Bazel-style, stdlib only).

Reads BUILD files that declare go_library / go_binary / go_test targets with
explicit srcs and deps, then builds the requested targets in dependency order.

Each target is compiled in an isolated staging tree that contains ONLY the
sources reachable through its DECLARED dependency edges (its transitive dep
closure). A target that imports a package it does not declare (directly or via
a declared dependency) will fail to compile, because that package's sources are
absent from the staging tree. Edges therefore matter, exactly like Bazel's
sandboxed builds -- unlike a bare `go build ./...`.

Usage: build.py //...            build every target
       build.py //cmd/app:app    build one target and its dep closure
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MODULE = "example.com/monorepo"
BIN = os.path.join(ROOT, "bazel-bin")
OUT = os.path.join(ROOT, "bazel-out")
LOG = os.path.join(OUT, "build.log")
_SKIP = {"bazel-bin", "bazel-out"}

TARGETS = {}


def _register(kind, pkg, name, srcs, deps):
    label = "//%s:%s" % (pkg, name) if pkg else "//:%s" % name
    norm = []
    for d in deps:
        if d.startswith(":"):
            norm.append(("//%s:%s" % (pkg, d[1:])) if pkg else ("//:" + d[1:]))
        else:
            norm.append(d)
    TARGETS[label] = {
        "kind": kind, "pkg": pkg, "name": name,
        "srcs": list(srcs), "deps": norm, "label": label,
    }


def _load():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        top = rel.split(os.sep)[0]
        if top in _SKIP:
            dirnames[:] = []
            continue
        if "BUILD" not in filenames:
            continue
        pkg = "" if rel == "." else rel.replace(os.sep, "/")
        ns = {
            "go_library": (lambda name, srcs=(), deps=(), _p=pkg:
                           _register("go_library", _p, name, srcs, deps)),
            "go_binary": (lambda name, srcs=(), deps=(), _p=pkg:
                          _register("go_binary", _p, name, srcs, deps)),
            "go_test": (lambda name, srcs=(), deps=(), _p=pkg:
                        _register("go_test", _p, name, srcs, deps)),
        }
        path = os.path.join(dirpath, "BUILD")
        with open(path) as f:
            exec(compile(f.read(), path, "exec"), ns, ns)


def _closure(label, seen):
    if label in seen:
        return
    if label not in TARGETS:
        raise SystemExit("unknown dependency label: %s" % label)
    seen.add(label)
    for d in TARGETS[label]["deps"]:
        _closure(d, seen)


def _toposort(labels):
    order, perm, temp = [], set(), set()

    def visit(l):
        if l in perm:
            return
        if l in temp:
            raise SystemExit("dependency cycle at %s" % l)
        temp.add(l)
        for d in sorted(TARGETS[l]["deps"]):
            visit(d)
        temp.discard(l)
        perm.add(l)
        order.append(l)

    for l in sorted(labels):
        visit(l)
    return order


def _build_one(label):
    t = TARGETS[label]
    seen = set()
    _closure(label, seen)
    stage = tempfile.mkdtemp(prefix="build-")
    try:
        with open(os.path.join(stage, "go.mod"), "w") as f:
            f.write("module %s\n\ngo 1.26\n" % MODULE)
        for dep in seen:
            dt = TARGETS[dep]
            ddir = os.path.join(stage, dt["pkg"]) if dt["pkg"] else stage
            os.makedirs(ddir, exist_ok=True)
            for s in dt["srcs"]:
                shutil.copy(os.path.join(ROOT, dt["pkg"], s),
                            os.path.join(ddir, s))
        pkgpath = MODULE + ("/" + t["pkg"] if t["pkg"] else "")
        if t["kind"] == "go_binary":
            outdir = os.path.join(BIN, t["pkg"])
            os.makedirs(outdir, exist_ok=True)
            cmd = ["go", "build", "-o", os.path.join(outdir, t["name"]), pkgpath]
        elif t["kind"] == "go_test":
            cmd = ["go", "test", pkgpath]
        else:
            cmd = ["go", "build", "-o", os.devnull, pkgpath]
        proc = subprocess.run(cmd, cwd=stage, capture_output=True, text=True)
        if proc.returncode != 0:
            sys.stderr.write("BUILD FAILED %s\n%s%s\n"
                             % (label, proc.stdout, proc.stderr))
            return False
        if t["kind"] == "go_test":
            mdir = os.path.join(BIN, t["pkg"])
            os.makedirs(mdir, exist_ok=True)
            with open(os.path.join(mdir, t["name"] + ".testresult"), "w") as f:
                f.write("PASS\n")
        return True
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def main(argv):
    arg = argv[0] if argv else "//..."
    _load()
    if arg == "//...":
        labels = list(TARGETS.keys())
    else:
        seen = set()
        _closure(arg, seen)
        labels = list(seen)
    shutil.rmtree(BIN, ignore_errors=True)
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT, exist_ok=True)
    order = _toposort(labels)
    with open(LOG, "w") as logf:
        for i, label in enumerate(order, 1):
            if not _build_one(label):
                logf.write("FAILED %s\n" % label)
                print("build failed: %s" % label)
                return 1
            logf.write("BUILT %d %s\n" % (i, label))
            logf.flush()
            print("BUILT %s" % label)
        logf.write("OK\n")
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
