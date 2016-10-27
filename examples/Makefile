SOURCES=$(wildcard *.c)
LDFLAGS=-lrt -pthread
CFLAGS=-g

all: bins 100mb 10mb

bins: $(SOURCES:.c=)

100mb: 
	dd if=/dev/urandom of=$@ bs=1024 count=102400

10mb: 
	dd if=/dev/urandom of=$@ bs=1024 count=10240
