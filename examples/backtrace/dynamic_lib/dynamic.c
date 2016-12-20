#include <stdio.h>

void fn(void(*cb)()) {
	printf("HELLO\n");
	fflush(stdout);
	cb();
}
