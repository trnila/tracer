#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <signal.h>
#include <wait.h>

int main() {
	pid_t child = fork();
	if(child == 0) {
		printf("Waiting to be killed\n");
		pause();

		exit(0);
	}

	sleep(1);

	kill(child, SIGKILL);

	while(wait(NULL) > 0);
}
