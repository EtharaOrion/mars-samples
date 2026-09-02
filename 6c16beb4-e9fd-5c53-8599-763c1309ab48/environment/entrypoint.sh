#!/bin/bash
python3 /srv/https-mock/server.py > /tmp/mock.log 2>&1 &
sleep 2
exec sleep infinity
