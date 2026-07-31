#!/bin/bash
cd /app

files=0
records=0
units=0

for f in $(ls data); do
    files=$((files + 1))
    while read qty name; do
        records=$((records + 1))
    done < data/$f
done

cat data/* | while read qty name; do
    units=$((units + qty))
done

products=""
for f in $(ls data); do
    while read qty name; do
        products="$products $name"
    done < data/$f
done
pcount=$(echo $products | tr ' ' '\n' | sort -u | grep -c .)

{
    echo "files=$files"
    echo "records=$records"
    echo "units=$units"
    echo "products=$pcount"
} > report.txt
