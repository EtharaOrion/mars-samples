#!/bin/sh
set -eu
sum=0
while IFS= read -r n; do
  [ -z "$n" ] && continue
  sum=$((sum + n))
done < /nested/values.txt
sha=$(sha256sum /nested/values.txt | cut -c1-16)
printf 'NESTED-OK sum=%s sha=%s\n' "$sum" "$sha"
