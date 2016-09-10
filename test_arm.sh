#!/bin/bash
HOST=build@pi
BUILD_DIR=/tmp/$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 10 | head -n 1)

clean() {
	echo cleaning up
	ssh $HOST "rm -r $BUILD_DIR"
}

trap clean EXIT

ssh $HOST "mkdir -p $BUILD_DIR"
rsync -avz . $HOST:$BUILD_DIR/.

ssh $HOST 'bash -s' <<BUILD
set -ex
cd $BUILD_DIR
source ~/tracer/bin/activate
python test.py
BUILD
