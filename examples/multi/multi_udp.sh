#!/bin/sh
TOTAL=1
set -x

if [ ! -z $1 ]; then
	TOTAL=$1
fi

tracer -o /tmp/report1 -- ./examples/sockets/udp_server.py &
sleep 2

for i in $(seq 2 $(($TOTAL+1))); do
	sleep 2
	echo $i
	tracer -o /tmp/report$i -- sh -c "echo $i > /dev/udp/127.0.0.1/12345"
done

echo "done, killing!, error may be visible, thats okay"
sleep 2
ps a | grep -E "python .+udp_server.py"
kill $( ps a | grep -E "python .+udp_server.py"  | grep -v tracer | cut -f 1 -d' ')
echo killed
