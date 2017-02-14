#include "common.h"

const char request[] = "GET / HTTP/1.0\n\n";

int main(int argc, char *argv[]) {
	struct addrinfo *hints;
	parse(argc, argv, &hints);

	for_each(hints, [](int sock, struct addrinfo *p) -> void {
		if(bind(sock, p->ai_addr, p->ai_addrlen) == -1) {
			perror("connect");
			return;
		}

		listen(sock, 10);

		socklen_t size;
		struct sockaddr addr;
		int client = accept(sock, &addr, &size);

		char buffer[100];
		int n = read(client, buffer, sizeof(buffer));
		for(int i = 0; i < n; i++) {
			buffer[i]++;
		}
		write(client, buffer, n);
	});

    return 0;
}
