#!/bin/bash
HOST=build@pi.home.trnila.eu
BUILD_DIR=/tmp/$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 10 | head -n 1)
SSH_ARGS=

if [ -f .travis_key ]; then
	SSH_ARGS="$SSH_ARGS -i .travis_key"
fi

clean() {
	echo cleaning up
	ssh $SSH_ARGS $HOST "rm -r $BUILD_DIR"
}

trap clean EXIT

ssh $SSH_ARGS $HOST "mkdir -p $BUILD_DIR"
rsync -e "ssh $SSH_ARGS" -avz . $HOST:$BUILD_DIR/.

ssh $SSH_ARGS $HOST 'bash -s' <<BUILD
set -ex
cd $BUILD_DIR
source ~/tracer/bin/activate
python test.py
BUILD
