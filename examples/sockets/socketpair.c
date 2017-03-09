#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>

#define PACKET_SIZE 32
#define WORKERS 5

int main() {
    int pair[2];
    char buff[PACKET_SIZE];
    int len;
    memset(buff, ' ', sizeof(buff));

    if(socketpair(AF_UNIX, SOCK_STREAM, 0, pair) < 0) {
        perror("socketpair");
        return 1;
    }


    if(!fork()) {
        printf("Collector started\n");
        close(pair[0]);
        while((len = read(pair[1], buff, sizeof(buff))) > 0) {
            buff[len] = 0;
            printf("collected: %s\n", buff);
        }
        exit(0);
    }

    for(int i = 0; i < WORKERS; i++) {
        if(!fork()) {
            int len = snprintf(buff, sizeof(buff), "%d Hello", i);
            write(pair[1], buff, PACKET_SIZE);

            exit(0);
        }
    }

    close(pair[1]);
    int remaining = WORKERS;
    // XXX: partial messages
    while(remaining && (len = read(pair[0], buff, sizeof(buff))) > 0) {
        for(int i = 0; i < strlen(buff); i++) {
            if(buff[i] > 'a' && buff[i] < 'z') {
               buff[i] += 'Z' - 'z';
            }
        }

        write(pair[0], buff, len);
        remaining--;
    }
    close(pair[0]);
    close(pair[1]);
    printf("finished\n");

    while(wait() > 0);
    return 0;
}