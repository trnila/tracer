#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <signal.h>
#include <wait.h>

int parent;

int received = 0;
void childHandler(int sig) {
	printf("[child] received: %d\n", sig);
	received = 1;
}

void parentHandler(int sig) {
	printf("[parent] received: %d\n", sig);
}


int main() {
	parent = getpid();
	pid_t child = fork();
	if(child == 0) {
		signal(SIGUSR1, childHandler);
		sleep(1);
		kill(parent, SIGUSR1);
		sleep(2);

		exit(0);
	}
	signal(SIGUSR1, parentHandler);

	sleep(1);

	kill(child, SIGUSR1);

	while(wait(NULL) > 0);
}
