#include "common.h"

const char request[] = "GET / HTTP/1.0\n\n";

int main(int argc, char *argv[]) {
	struct addrinfo *hints;
	parse(argc, argv, &hints);

	for_each(hints, [](int sock, struct addrinfo *p) -> void {
		if(connect(sock, p->ai_addr, p->ai_addrlen) == -1) {
			perror("connect");
			return;
		}

		write(sock, request, strlen(request));
		char buffer[1024];
		int n;
		while((n = read(sock, buffer, sizeof(buffer)))) {
			write(1, buffer, n);
		}

	});

    return 0;
}
