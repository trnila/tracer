#include <sys/mman.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>



int main() {
	int size = 128;
	char* map = (char*) mmap(0, size, PROT_READ|PROT_WRITE, MAP_ANONYMOUS|MAP_SHARED, -1, 0);
	if(map <= 0) {
		perror("mmap");
		return 1;
	}

	map[0] = '-';
	if(fork() == 0) {
		while(map[0] != 'Q') {
			printf("%c\n", map[0]);
			if(map[0] == 'C') {
				int a, b;
				sscanf(map + 1, "%d %d", &a, &b);
				sprintf(map + 1, "%d", a + b);
				map[0] = 'D';
				printf("%d + %d = %d\n", a, b, a + b);
			}

			usleep(1000);
		}
		

		exit(0);
	}

	for(int i = 0; i < 10; i++) {
		snprintf(map + 1, size, "%d %d", i, i+1);
		map[0] = 'C';

		while(map[0] != 'D') {
			usleep(1000);
		}
		printf("got result\n");
	}

	map[0] = 'Q';
	while(wait(NULL) > 0);
}
