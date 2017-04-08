#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>

void main() {
    int fd = open("/tmp/file", O_RDWR | O_CREAT, 0600);
    if(fd < 0) {
        perror("open");
        exit(1);
    }

    int len = 128;
    if(ftruncate(fd, len) != 0) {
        perror("ftruncate");
        exit(1);
    }

    char *addr = mmap(0, len, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);

    for(int i = 0; i < 100; i++) {
        sprintf(addr, "%d", i);
        write(1, ".", 1);
    }
}