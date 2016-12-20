#include <stdio.h>

void test1(void(*callback)(const char*)) {
	printf("TEST\n");
	fflush(stdout);
	callback("TEST2");
}

void test(void(*callback)(const char*)) {
	test1(callback);
}
