#include <stdio.h>

void fn(void(*cb)());

void mycb() {
	printf("cb\n");
	fflush(stdout);
}

int main() {
	fn(mycb);
}