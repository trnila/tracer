#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <signal.h>
#include <wait.h>

void handler(int sig) {}

int main() {
	int parent = getpid();
	pid_t child = fork();
	if(child == 0) {
		sleep(1);
		kill(parent, SIGUSR1);

		exit(0);
	}
	signal(SIGUSR1, handler);

	pause();

	while(wait(NULL) > 0);
}
