CXXFLAGS=-fPIC -g
LDFLAGS=-lunwind -lunwind-x86_64 -lunwind-ptrace

all: backtrace.so a

backtrace.so: backtrace.o
	g++ $^ $(LDFLAGS) -shared -o $@

clean:
	rm -f *.o *.so
