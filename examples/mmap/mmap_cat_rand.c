#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
	int fd = open("/etc/services", O_RDONLY);
	lseek(fd, 0, SEEK_END);
	int len = lseek(fd, (size_t) 0, SEEK_CUR);
	lseek(fd, 0, SEEK_SET);


	printf("%d\n", len);
	char *addr = mmap(0, len, PROT_READ, MAP_PRIVATE, fd, 0);
	if(!addr) {
		perror("mmap\n");
		exit(1);
	}

	while(*addr != '\n') {
		putchar(*addr);
		addr++;
	}

	addr += 10240;
	while(*addr != '\n') {
		putchar(*addr);
		addr++;
	}

	return 0;
}
