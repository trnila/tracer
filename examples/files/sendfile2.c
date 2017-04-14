#include <sys/sendfile.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/stat.h>

int main() {
	int fd = open("/etc/passwd", O_RDONLY);
	if(fd < 0) {
		perror("open");
		exit(1);
	}

	struct stat buf;
	if(fstat(fd, &buf) != 0) {
		perror("fstat");
		exit(1);
	}

	int dst = open("/tmp/file", O_WRONLY|O_CREAT|O_TRUNC);
	if(dst < 0) {
	    perror("open");
	    exit(1);
	}

	int ret = sendfile(dst, fd, NULL, buf.st_size);
	perror("sendfile");
	printf("return: %d\n", ret);

	return 0;
}
