#include "common.h"

int main() {
    const char name[] = "test";
    int size = 1024;

	if(fork() == 0) {
		char* mem = create_share_mem(name, size);

		while(strcmp("hello", mem)) {
			printf(".");
			usleep(50000);
		}
		printf("ending\n");

		exit(0);
	}

	char* mem = create_share_mem(name, size);

	usleep(250000);
	strcpy(mem, "hello");

	while(wait(NULL) > 0);

	shm_unlink(name);

	return 0;
}
