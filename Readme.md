# tracer

## Standalone usage
```sh
git clone https://github.com/trnila/tracer.git
cd tracer
virtualenv tracer
source tracer/bin/activate
pip install python-ptrace
```
### Usage
```sh
source tracer/bin/activate
./tracer.py -o /tmp/report -- sh -c "curl httpbin.com/headers ; cat /etc/passwd | tr a-z A-Z | tac"
```

## Using bootstrap (includes gui)
```sh
curl https://raw.githubusercontent.com/trnila/tracer/master/bootstrap.sh | sh
cd tracer
./run.sh sh -c "curl httpbin.com/headers ; cat /etc/passwd | tr a-z A-Z | tac"
```
