# tracer

## installation

```sh
git clone https://github.com/trnila/tracer.git
cd tracer
virtualenv tracer
source tracer/bin/activate
pip install python-ptrace
```

## usage
```sh
./tracer/bin/python strace.py -o /tmp/report -- sh -c "curl httpbin.com/headers ; cat /etc/passwd | tr a-z A-Z | tac"
```
