#include <openssl/ssl.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <dlfcn.h>
#include <unistd.h>

int SSL_read(SSL *ssl, void *buf, int num) {
	int ret = ((int(*)(SSL*, void *, int )) dlsym(RTLD_NEXT, "SSL_read"))(ssl, buf, num);

	int sock = socket(AF_UNIX, SOCK_STREAM, 0);
	if(sock < 0) {
		perror("socket");
		return ret;
	}

	struct sockaddr_un addr;
	memset(&addr, 0, sizeof(addr));
	addr.sun_family = AF_UNIX;
	strncpy(addr.sun_path, "/tmp/a", sizeof(addr.sun_path)-1);

	if(connect(sock, (struct sockaddr *) &addr, sizeof(struct sockaddr_un)) == -1) {
		perror("connect");
		return ret;
	}


	int pid = getpid();
	write(sock, &pid, sizeof(pid));
	sleep(1);

	char action = 0;
	write(sock, &action, sizeof(action));
	sleep(1);

	int fd = SSL_get_rfd(ssl);
	write(sock, &fd, sizeof(fd));
	sleep(1);

	write(sock, &num, sizeof(num));
	sleep(1);
	write(sock, buf, num);

	((char*)buf)[num] = 0;
	fprintf(stderr, ">>%s<< %d\n", buf, fd);
	return ret;
}
