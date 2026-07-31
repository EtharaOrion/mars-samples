#!/bin/sh
set -e
cd /app

# Deterministic OFFLINE build: all Gradle machinery + dependencies were cached
# into the image at docker-build time; no network is required or permitted here.
gradle --no-daemon --offline clean build >/tmp/gradle_build.log 2>&1 || {
    echo "BUILD_FAILED (gradle --offline build exit nonzero)"
    tail -30 /tmp/gradle_build.log
    exit 1
}

JAR=app/build/libs/app.jar
if [ ! -f "$JAR" ]; then
    echo "NO_JAR: $JAR not produced"
    exit 1
fi

out=$(java -jar "$JAR")
expected="widget-core checksum=6562704"
if [ "$out" != "$expected" ]; then
    echo "BAD_OUTPUT: got [$out] want [$expected]"
    exit 1
fi

# Test suite must have executed and produced zero failures/errors.
xml=$(ls app/build/test-results/test/*.xml 2>/dev/null | head -1 || true)
if [ -z "$xml" ]; then
    echo "NO_TEST_RESULTS: JUnit XML not found"
    exit 1
fi
fails=$(grep -o 'failures="[0-9]*"' "$xml" | grep -o '[0-9]*')
errs=$(grep -o 'errors="[0-9]*"' "$xml" | grep -o '[0-9]*')
tests=$(grep -o 'tests="[0-9]*"' "$xml" | grep -o '[0-9]*')
if [ "$fails" != "0" ] || [ "$errs" != "0" ]; then
    echo "TESTS_FAILED: failures=$fails errors=$errs"
    exit 1
fi
if [ -z "$tests" ] || [ "$tests" -lt 1 ]; then
    echo "NO_TESTS_RAN"
    exit 1
fi
