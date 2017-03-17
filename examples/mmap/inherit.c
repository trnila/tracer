#include <stdio.h>
#include <sys/mman.h>
#include <unistd.h>

int main() {
	mmap(0, 128, PROT_READ, MAP_SHARED|MAP_ANONYMOUS, -1, 0);
	mmap(0, 129, PROT_READ, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
	fork();
}
