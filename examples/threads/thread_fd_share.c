#include <stdio.h>
#include <pthread.h>

FILE *sharedFd;

void* fn(void *arg) {
	fprintf(sharedFd, "thread");
	fflush(sharedFd);
}

int main() {
	sharedFd = fopen("/tmp/file", "w");
	fprintf(sharedFd, "process");
	fflush(sharedFd);

	pthread_t t;
	pthread_create(&t, NULL, fn, NULL);
	pthread_join(t, NULL);

	return 0;
}