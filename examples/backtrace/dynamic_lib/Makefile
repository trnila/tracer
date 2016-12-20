all: libdynamic.so main

libdynamic.so: dynamic.o
	gcc -g $^ -shared -o $@

dynamic.o: dynamic.c
	gcc -g $^ -c -fPIC -o $@

main: main.o
	gcc -g $^ -o $@ -L. -ldynamic

clean:
	rm -f *.o main libdynamic.so