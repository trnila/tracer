#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/stat.h>

int main() {
	int fd = open("/etc/passwd", O_RDONLY);

	struct stat buf;
	fstat(fd, &buf);

	char *addr;
	addr = mmap(0, buf.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
	printf("%s\n\n", addr);

	addr = mmap(0, buf.st_size, PROT_READ, MAP_SHARED, fd, 0);
	printf("%s", addr);



	return 0;
}
