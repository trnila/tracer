#include <string.h>

const char* getFilePath(char *dst, int size, const char *fileName) {
	if(readlink("/proc/self/exe", dst, size) == -1) {
		perror("readlink: ");
		exit(1);
	}

	char *last = strrchr(dst, '/');
	if(!last) {
		printf("Failed getting binary executable");
		exit(1);
	}

	strcpy(last + 1, fileName); // TODO: strncpy
	return dst;
}