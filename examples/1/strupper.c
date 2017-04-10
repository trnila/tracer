#include <stdio.h>

int main() {
	char c;
	while((c = getchar()) != EOF) {
		if(c >= 'a' && c <= 'z') {
			putchar(c - ('z' - 'Z'));
		} else {
			putchar(c);
			if(c == '\n') fflush(stdout);
		}
	}

	return 0;
}
