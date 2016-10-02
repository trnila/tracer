REMOTE=192.168.1.4
DST=/tmp/tracer

rsync -avz . $REMOTE:$DST


python strace.py -o /tmp/report1 -- sh -c 'cat /proc/cpuinfo | nc -l 1234' &
sleep 2

ssh $REMOTE python $DST/strace.py -o /tmp/report2 -- nc 192.168.1.2 1234
rsync -avz $REMOTE:/tmp/report2/ /tmp/report2

