#!/bin/bash
set -e
mkdir tracer
cd tracer

virtualenv -p python3 python
source python/bin/activate
pip install python-ptrace

git clone https://github.com/trnila/tracer.git -b develop
(
	cd tracer
	make -C backtrace
)

git clone https://github.com/trnila/tracer-gui.git gui -b develop
(
	cd gui
	pip install -r requirements.txt
)


cat << "EOF" > run.sh
#!/bin/bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
rm -rf /tmp/report1

source "$DIR/python/bin/activate"

"$DIR/tracer/tracer.py"  -s -b -o /tmp/report1  -- "$@"
"$DIR/gui/app.py" /tmp/report1
EOF

chmod +x run.sh
