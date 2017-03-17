# tracer [![Build Status](https://travis-ci.org/trnila/tracer.svg?branch=master)](https://travis-ci.org/trnila/tracer) [![Documentation Status](http://readthedocs.org/projects/tracertool/badge/?version=latest)](http://tracertool.readthedocs.io/en/latest/?badge=latest)

## Dependencies
- at least Python 3.2
- libunwind
- addr2line


## Installation
To install development version from branch master run:
```sh
pip3 install git+https://github.com/trnila/tracer.git
```

Optional dependencies are *colorlog* and *ipython* so if you want to have better interface install them:
```sh
pip3 install colorlog ipython
```

### Installation with virtualenv on Ubuntu 16.10
```
sudo apt-get install python-virtualenv python3-dev git libunwind8-dev python3-pip
virtualenv -p python3 venv3
source venv3/bin/activate
pip3 install git+https://github.com/trnila/tracer.git
pip3 install colorlog ipython # optional
```

## Usage
```sh
tracer -- sh -c "curl httpbin.com/headers ; cat /etc/passwd | tr a-z A-Z | tac" 
```

For more information about options run
```sh
tracer -h
```

## Examples
If you clone this repository somewhere, you can run interesting examples though helper script `./examples/run`,
but it requires `tracer` and [`tracergui`](https://github.com/trnila/tracer-gui) in your *PATH*. 
It can be achieved by installing both applications with *
*.  

## Documentation
More information is available in [documentation](http://tracertool.readthedocs.io/en/latest/).

## Development
```sh
git clone https://github.com/trnila/tracer
cd tracer
python setup.py develop
```

### Tests
Run `python -m unittest` or `pytest` if you have pytest installed.
