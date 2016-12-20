#include <stdio.h>
void test(void(*callback)(const char*));

void mycallback(const char* str) {
	printf("%s\n", str);
	fflush(stdout);
}

int main() {
	test(mycallback);
}