#!/bin/sh
id -u | sed 's/^/UID=/'
head -n 1 /mnt/owned.txt | sed 's/^/READ=/'
if printf 'MARK-7B2C\n' >> /mnt/owned.txt; then
  echo WROTE=ok
else
  echo WROTE=denied
fi
