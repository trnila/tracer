#!/bin/sh
TOTAL=1

if [ ! -z $1 ]; then
	TOTAL=$1
fi

tracer -o /tmp/report1 -- sh -c 'cat /proc/cpuinfo | nc -k -l 1234' &

for i in $(seq 2 $(($TOTAL+1))); do
	sleep 2
	echo $i
	tracer -o /tmp/report$i -- sh -c "echo $i | nc localhost 1234"
done

sleep 2
kill $(pidof nc)
echo killed
