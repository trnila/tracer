#!/bin/sh

if ! $(grep $USER /etc/pazzwd &> /dev/null) ; then
    echo "You are not in passwd??"
else
    echo "What?"
fi