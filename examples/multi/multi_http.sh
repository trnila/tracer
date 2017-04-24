#!/bin/sh
tracer -o /tmp/report1 -- timeout 60 python -m http.server &
PID=$!
sleep 15
echo "running clients"
tracer -o /tmp/report2 -- bash -c "echo GET /multi_nc.sh | nc localhost 8000"
tracer -o /tmp/report3 -- curl localhost:8000/remote_nc.sh

echo "wait until python http server will shut down"
wait $PID
echo "now you can run tracerui /tmp/report{1,2,3}"
