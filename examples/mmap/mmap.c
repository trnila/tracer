#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>

int main() {
	int fd;
	const char str[] = "Hello world!";
	int len = strlen(str);;

	fd = open("/tmp/file", O_CREAT | O_RDWR, 0600);
	write(fd, str, len);


	char *addr;
	addr = mmap(0, len, PROT_READ, MAP_PRIVATE, fd, 0);
	printf("%s\n\n", addr);
	munmap(addr, len);

	addr = mmap(0, len, PROT_READ, MAP_SHARED, fd, 0);
	printf("%s", addr);
	munmap(addr, len);

	addr = mmap(0, len, PROT_WRITE, MAP_SHARED, fd, 0);
	addr[0] = 'h';
	munmap(addr, len);

	return 0;
}
