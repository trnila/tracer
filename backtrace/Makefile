CFLAGS=-fPIC
LDFLAGS=-lunwind -lunwind-x86_64 -lunwind-ptrace

all: backtrace.so a

backtrace.so: backtrace.o
	gcc $^ $(LDFLAGS) -shared -o $@

clean:
	rm -f *.o *.so
