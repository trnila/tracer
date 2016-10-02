TOTAL=1

if [ ! -z $1 ]; then
	TOTAL=$1
fi

python strace.py -o /tmp/report1 -- ./examples/udp_server.py &

for i in $(seq 2 $(($TOTAL+1))); do
	sleep 2
	echo $i
	python strace.py -o /tmp/report$i -- sh -c "echo $i > /dev/udp/127.0.0.1/1234"
done

sleep 2
kill $( ps a | grep -E "python /.+udp_server.py" | cut -f 1 -d' ')
echo killed
