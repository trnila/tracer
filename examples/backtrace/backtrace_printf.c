#include <stdio.h>
#include <unistd.h>
#include <string.h>

#define FN(msg); write(1, msg, strlen(msg));

int a() {
	FN("a\n");
}

int b() {
	a();
	FN("b\n");
}

int main() {
	b();
	FN("c\n");
}
