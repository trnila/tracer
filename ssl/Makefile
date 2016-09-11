all: preload.so

preload.so: preload.o
	g++ $^ -shared -o $@ -ldl

preload.o: preload.cpp
	g++ $^ -c -fpic

clean:
	rm -f *.o preload.so
