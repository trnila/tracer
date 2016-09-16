# tracer

## installation

```sh
$ git clone https://github.com/trnila/tracer.git
$ cd tracer
$ virtualenv tracer
$ source tracer/bin/activate
$ hg clone https://bitbucket.org/MichaelHTW/python-ptrace-withclone /tmp/ptrace
$ (cd /tmp/ptrace/ && python setup.py install)
```

## usage
```sh
$ ./tracer/bin/python strace.py -o /tmp/report -- sh -c "curl httpbin.com/headers ; cat /etc/passwd | tr a-z A-Z | tac"
```
