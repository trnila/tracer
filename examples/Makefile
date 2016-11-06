STANDALONE=$(shell find **/ -type f -name "Makefile" -exec dirname {} \;)
SOURCES=$(shell find -name "*.c" ! -path './backtrace/dynamic_lib*' ! -path './backtrace/more_sources*') #TODO: use STANDALONE
LDFLAGS=-lrt -pthread
CFLAGS=-g

all: bins standalone 100mb 10mb

bins: $(SOURCES:.c=)

standalone:
	for i in $(STANDALONE) ; do \
		make -C $$i ; \
	done

100mb: 
	dd if=/dev/urandom of=$@ bs=1024 count=102400

10mb: 
	dd if=/dev/urandom of=$@ bs=1024 count=10240

clean:
	rm -f $(SOURCES:.c=) exclude
	for i in $(STANDALONE) ; do \
		make -C $$i clean ; \
	done