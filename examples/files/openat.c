#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <dirent.h>

void print(int fd) {
	char buffer[128];
	int n;
	while((n = read(fd, buffer, sizeof(buffer))) > 0) {
		write(1, buffer, n);
	}
}

int main() {
	// open in current working dir
	int fd = open("requirements.txt", O_RDONLY);
	if(fd < 0) perror("open readme");
	print(fd);
	close(fd);

	// change working dir
	chdir("examples/files");
	fd = open("openat.c", O_RDONLY);
	if(fd < 0) perror("open chdired");
	print(fd);
	close(fd);

	int fdd = open("/etc", O_DIRECTORY);
	if(fdd < 0) {
		perror("opendir");
	}

	// open relative to descriptor dir
	fd = openat(fdd, "passwd", O_RDONLY);
	if(fd < 0) perror("open passwd");
	print(fd);
	close(fd);

	// absolute
	fd = openat(fdd, "/proc/meminfo", O_RDONLY);
	if(fd < 0) perror("open passwd");
	print(fd);
	close(fd);

	// relative to current working directory
	fd = openat(AT_FDCWD, "../Makefile", O_RDONLY);
	if(fd < 0) perror("open passwd");
	print(fd);
	close(fd);
}
