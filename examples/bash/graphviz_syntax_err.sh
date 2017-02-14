#!/bin/bash

ip a | awk -f <(cat - <<-'AWK'
BEGIN {
    print("digraph G {")
}

END {
    print("}")
}

/^([0-9])+:/ {
    interface = substr($2, 0, length($2) - 1)
    printf("\"%s\" -> \"%s\"\n", $2, interface)
}

/inet/ {
    printf("\"%s\" -> \"%s\n", $2, interface) # HERE IS MISSING "
}
AWK
) | dot -Tx11