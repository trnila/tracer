#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <stdio.h>


int main() {
	int fd = open("/etc/passwd", O_RDONLY | O_CLOEXEC);
	if(!fd) {
		perror("open");
		exit(1);
	}

	if(fork() == 0) {
		// shall not have fd open!
	}
}
