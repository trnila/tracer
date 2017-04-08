#include "common.h"

const int N = 3;
const int SIZE = 20;

int main() {
    const char name[] = "test";
    int size = N * SIZE;

    for(int i = 0; i < N; i++) {
        if(fork() == 0) {
            char* mem = create_share_mem(name, size);

            sprintf(mem + i * SIZE, "Hello from %d", i);
            usleep(500);
            printf("ending\n");
            exit(0);
        }
    }

	while(wait(NULL) > 0);

	shm_unlink(name);
	return 0;
}
