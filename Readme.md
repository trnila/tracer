# tracer

## Standalone usage
```sh
git clone https://github.com/trnila/tracer.git
cd tracer
virtualenv tracer
source tracer/bin/activate
pip install < requirements.txt
```
### Usage
```sh
source tracer/bin/activate
./tracer.py -o /tmp/report -- sh -c "curl httpbin.com/headers ; cat /etc/passwd | tr a-z A-Z | tac"
```

## Using bootstrap (includes gui)
### Dependencies
- python >= 3.4
- graphviz
- PyQt5
- libunwind (optional, for backtraces)
- addr2line (optional, for backtraces)

#### Archlinux
```sh
pacman -S base-devel git python-virtualenv graphviz
```

#### Debian
```sh
apt-get install curl git virtualenv make gcc g++ libunwind-dev graphviz python3-pyqt5
```

#### Ubuntu 14.04
```sh
apt-get install curl git python-virtualenv make gcc g++ libunwind8-dev graphviz python3-pyqt5
```

#### Installation
```sh
curl https://raw.githubusercontent.com/trnila/tracer/master/bootstrap.sh | sh
cd tracer
./run.sh sh -c "curl httpbin.com/headers ; cat /etc/passwd | tr a-z A-Z | tac"
```

## Tests
Just run `python -m unittest` or `pytest` if you have pytest installed.