#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <signal.h>
#include <wait.h>

void handler(int sig) {}

int main() {
	signal(SIGUSR1, handler);
	int parent = getpid();
	int child = fork();
	if(child == -1) {
		perror("fork");
		exit(1);
	} else if(child == 0) {
		sleep(1);
		kill(parent, SIGUSR1);

		exit(0);
	}

	pause();

	while(wait(NULL) > 0);
}
