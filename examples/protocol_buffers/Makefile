LDFLAGS=-lprotobuf
CC=g++

main: main.o book.pb.o

book.pb.cc: book.proto
	protoc --cpp_out=. $^


clean:
	rm -f *.o main book.pb.cc
