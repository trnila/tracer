#!/bin/bash

rm -rf /tmp/report1 /tmp/report2

REMOTE=ubuntu1604
THIS_HOST=192.168.1.2

tracer -o /tmp/report1 -- sh -c 'cat /proc/cpuinfo | nc -l 1234' &
sleep 2

ssh $REMOTE -t "
    if [ ! -d venv ]; then
        virtualenv -p python3 venv
        source venv/bin/activate
        pip3 install git+https://github.com/trnila/tracer.git
    else
        source venv/bin/activate
    fi

    tracer -o /tmp/report2 -- nc $THIS_HOST 1234
"
rsync -avz $REMOTE:/tmp/report2/ /tmp/report2

