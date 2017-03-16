#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <signal.h>
#include <wait.h>

int main() {
    int pipes[2];
    pipe(pipes);

	int child = fork();
	if(child == 0) {
	    close(pipes[0]);

		printf("Waiting to be killed\n");
		write(pipes[1], "R", 1);

		sleep(30);
		exit(0);
	}

    // wait until child is ready to die
    close(pipes[1]);
	char c;
	read(pipes[0], &c, 1);

	kill(child, SIGKILL);
	while(wait(NULL) > 0);
}
