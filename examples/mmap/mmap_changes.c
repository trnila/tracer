#include <sys/mman.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>

int main() {
	const char* str[] = {
		"Hello",
		"This is an example",
		"of memory",
		"of memory that is captured",
		"by mmap extension"
	};

	int size = 128;
	char* map = (char*) mmap(0, size, PROT_READ|PROT_WRITE, MAP_ANONYMOUS|MAP_PRIVATE, -1, 0);
	if(map <= 0) {
		perror("mmap");
		return 1;
	}
	
	for(int i = 0; i < sizeof(str)/sizeof(*str); i++) {
		strncpy(map, str[i], size);
		write(1, ".", 1); 
	}

}
