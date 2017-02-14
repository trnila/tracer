#!/bin/sh
addresses="$(ip addr | grep inet6 | grep -Ev 'link|host' | awk '{print $2}')"
echo -e "Your public ipv6 addresses are:\n$addresses"
echo "Count: " "$(echo """$addresses""" | wc -l)"
