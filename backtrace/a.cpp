#include <stdio.h>
#include <unistd.h>

int a() {
	write(1, "A\n", 2);
}

int b() {
	a();
	write(1, "B\n", 2);
}

int main() {
	b();
}
