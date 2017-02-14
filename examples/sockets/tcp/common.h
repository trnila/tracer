#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <getopt.h>
#include <unistd.h>
#include <stdlib.h>
#include <functional>


void print_usage(char *program) {
	printf("Usage: %s [-4|-6] [-t|-u] [-p port] server\n", program);
	exit(1);
}

int parse(int argc, char** argv, struct addrinfo **res) {
	char *port = nullptr;
	char *host;
	struct addrinfo hints;
	memset(&hints, 0, sizeof(hints));
	hints.ai_family = AF_UNSPEC;
	hints.ai_socktype = SOCK_STREAM;
	hints.ai_flags = AI_PASSIVE;

	int opt;
	while ((opt = getopt (argc, argv, "46p:")) != -1) {
		switch(opt) {
			case '4':
    			hints.ai_family = AF_INET;
				break;
			case '6':
    			hints.ai_family = AF_INET6;
				break;
			case 'p':
				port = optarg;
				break;
			default:
				print_usage(argv[0]);
		}
	}

	if(optind >= argc) {
		print_usage(argv[0]);
	}
	host = argv[optind];
	printf("%s %s\n", host, port);

	int status;
    if ((status = getaddrinfo(host, port, &hints, res)) != 0) {
        fprintf(stderr, "getaddrinfo: %s\n", gai_strerror(status));
        return 2;
    }
}

void for_each(struct addrinfo *res, std::function<void(int, struct addrinfo*)> cb) {
	struct addrinfo *p;
	int sock;

    for(p = res;p != NULL; p = p->ai_next) {
		if((sock = socket(p->ai_family, p->ai_socktype, p->ai_protocol)) == -1) {
			perror("socket");
			break;
		}

		cb(sock, p);		
		close(sock);
    }

}
