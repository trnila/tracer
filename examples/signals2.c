#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <signal.h>
#include <wait.h>

int parent;

void childHandler(int sig) {
}

void parentHandler(int sig) {
}


int main() {
	char c;
	parent = getpid();

	int pipes[2];
	pipe(pipes);
	pid_t child = fork();
	if(child == 0) {
		signal(SIGUSR1, childHandler);
		c = 'R';
		write(pipes[1], &c, 1);

		pause();

		kill(parent, SIGUSR2);
		exit(0);
	}
	close(pipes[1]);
	signal(SIGUSR2, parentHandler);

	if(read(pipes[0], &c, 1) != 1 || c != 'R') {
		perror("read");
		exit(1);
	}

	printf("[parent] Child is ready...\n");
	kill(child, SIGUSR1)
	printf("[parent] Sent signal to child...\n");

	while(wait(NULL) > 0);
	printf("[parent] End.\n");
}
