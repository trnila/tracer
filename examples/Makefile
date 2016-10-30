SOURCES=$(shell find -name "*.c")
LDFLAGS=-lrt -pthread
CFLAGS=-g

all: bins 100mb 10mb

bins: $(SOURCES:.c=)

100mb: 
	dd if=/dev/urandom of=$@ bs=1024 count=102400

10mb: 
	dd if=/dev/urandom of=$@ bs=1024 count=10240

clean:
	rm -f $(SOURCES:.c=)