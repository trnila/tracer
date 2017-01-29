python strace.py -o /tmp/report1 -- timeout 60 python -m http.server &
sleep 15
python strace.py -o /tmp/report2 -- sh -c "echo GET /test.py | nc localhost 8000"
python strace.py -o /tmp/report3 -- curl localhost:8000/strace.py 

