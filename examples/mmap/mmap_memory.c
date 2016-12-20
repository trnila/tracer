#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <wait.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>

const char *name = "test";

char* get_mem() {
	int size = 1024;

	int fd = shm_open(name,  O_CREAT | O_RDWR | O_EXCL, 0600);
	if(fd == -1) {
		if(errno == EEXIST) {
			fd = shm_open(name, O_RDWR, 0600);
			if(fd == -1) {
				perror("shm_open 2");
			}
		} else {
			perror("shm_open");
		}
	} else {
		ftruncate(fd, size);
	}

	char* addr = mmap(0, size, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
	printf("Got address 0x%X\n", addr);

	return addr;
}

int main() {
	if(fork() == 0) {
		char* mem = get_mem();

		while(strcmp("hello", mem)) {
			printf(".");
			usleep(50000);
		}
		printf("ending\n");

		exit(0);
	}

	char* mem = get_mem();

	usleep(250000);
	strcpy(mem, "hello");

	while(wait(NULL) > 0);



	shm_unlink(name);

	return 0;
}
