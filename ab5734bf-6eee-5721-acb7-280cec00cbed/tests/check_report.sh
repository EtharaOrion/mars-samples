#!/bin/sh
# WITHHELD golden report (author-computed with a correct reference implementation)
REPORT=/app/report.txt
if [ ! -f "$REPORT" ]; then
    echo "check_report: /app/report.txt missing"
    exit 1
fi
EXP="$(mktemp)"
printf 'files=3\nrecords=7\nunits=28\nproducts=5\n' > "$EXP"
if cmp -s "$REPORT" "$EXP"; then
    echo "check_report: ok"
    rm -f "$EXP"
    exit 0
fi
echo "check_report: report.txt does not match golden"
echo "--- expected ---"; cat "$EXP"
echo "--- got ---"; cat "$REPORT"
rm -f "$EXP"
exit 1
