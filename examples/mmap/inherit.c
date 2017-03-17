#include <stdio.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdlib.h>
#include <wait.h>

int main() {
	if(!mmap(0, 128, PROT_READ, MAP_SHARED|MAP_ANONYMOUS, -1, 0)) {
	    perror("mmap 128");
	    exit(1);
	}
	if(!mmap(0, 129, PROT_READ, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0)) {
	    perror("mmap 129");
	    exit(1);
	}

	int pid = fork();
    if(pid < 0) {
        perror("fork");
        exit(1);
    } else if(pid != 0) {
        while(wait(0) > 0);
    }
}
