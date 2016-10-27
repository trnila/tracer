#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <string.h>

const char* getFilePath(char *dst, int size, const char *fileName) {
	if(readlink("/proc/self/exe", dst, size) == -1) {
		perror("readlink: ");
		exit(1);
	}

	char *last = strrchr(dst, '/');
	if(!last) {
		printf("Failed getting binary executable");
		exit(1);
	}

	strcpy(last + 1, fileName); // TODO: strncpy
	return dst;
}


int main() {
	int fd;
	char buffer[250];
	const char* file = getFilePath(buffer, sizeof(buffer), "100mb");
	printf("%s\n", file);
	fd = open(file, O_RDONLY);
	if(!fd) {
		perror("open");
		exit(1);
	}

	struct stat buf;
	fstat(fd, &buf);
	int len = buf.st_size;

	FILE* f = fopen("/tmp/pid", "w");
	fprintf(f, "%d", getpid());
	fclose(f);

	char *addr = mmap(0, len, PROT_READ, MAP_PRIVATE, fd, 0);
	printf("%d-%d", addr[0], addr[len - 1]);

	return 0;
}
