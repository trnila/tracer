#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/wait.h>

int with_thread = 1;

int main() {
	int fd;
	const char* file = "100mb";
	fd = open(file, O_RDONLY);
	if(!fd) {
		perror("open");
		exit(1);
	}

	struct stat buf;
	fstat(fd, &buf);
	int len = buf.st_size;

	char *addr;
	addr = mmap(0, len, PROT_READ, MAP_PRIVATE, fd, 0);

	printf("%d %d\n", getpid(), addr);

	FILE* f = fopen("/tmp/pid", "w");
	fprintf(f, "%d", getpid());
	fclose(f);

	if(with_thread) {
		// try access first page
		printf("%d", addr[150]);
	}

	//getchar();
	if((with_thread && fork() == 0) || !with_thread) {
		int bulk = 10240;
		for(int i = 0; i < len / bulk; i++) {
			printf("%d", addr[i*bulk]);
			fflush(stdout);
			usleep(100000);
		}
	}

	while(wait(NULL) > 0);

	return 0;
}
