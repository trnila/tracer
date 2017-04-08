STANDALONE=$(shell find . ! -path ./Makefile ! -path ./ansible/Makefile -type f -name "Makefile" -exec dirname {} \;)
SOURCES=$(shell find -name "*.c" ! -path './backtrace/dynamic_lib*' ! -path './backtrace/more_sources*') #TODO: use STANDALONE
LDFLAGS=-pthread
CFLAGS=-g -std=gnu99
CC=gcc

all: bins standalone 100mb 10mb

bins: $(SOURCES:.c=)

mmap/mmap: mmap/mmap.c
	$(CC) $(CFLAGS) -o $@ $^ -lrt

mmap/mmap_memory: mmap/mmap_memory.c
	$(CC) $(CFLAGS) -o $@ $^ -lrt

mmap/share_nonparent: mmap/share_nonparent.c
	$(CC) $(CFLAGS) -o $@ $^ -lrt

standalone:
	for i in $(STANDALONE) ; do \
		make -C $$i ; \
	done

100mb: 
	dd if=/dev/urandom of=$@ bs=1024 count=102400
	echo -n Hello World | dd of=$@ conv=notrunc
	echo -n END OF FILE | dd of=100mb conv=notrunc seek=104857589 bs=1 # $(($(wc -c < 100mb)-11))

10mb: 
	dd if=/dev/urandom of=$@ bs=1024 count=10240

clean:
	rm -f $(SOURCES:.c=) 100mb 10mb 
	for i in $(STANDALONE) ; do \
		make -C $$i clean ; \
	done
