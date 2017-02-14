#!/bin/sh
tracer -o /tmp/report1 -- timeout 60 python -m http.server &
sleep 15
tracer -o /tmp/report2 -- sh -c "echo GET /Readme.md | nc localhost 8000"
tracer -o /tmp/report3 -- curl localhost:8000/Makefile
