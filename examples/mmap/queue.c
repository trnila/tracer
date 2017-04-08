#include <semaphore.h>
#include <errno.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <string.h>

#define PRODUCERS 5
#define PRODUCTS 10
#define MAX_SIZE 5

struct Queue {
	int head;
	int tail;
	char letters[MAX_SIZE];
};

struct Data {
	sem_t lock;
	sem_t fill;
	sem_t empty;
	struct Queue queue;
};


void producer(struct Data* data, int worker) {
	for(int i = 0; i < PRODUCTS; i++) {
		char letter = 'A' + i;
		sem_wait(&data->empty);

		sem_wait(&data->lock);
		printf("[%d] adding %c\n", worker, letter);
		data->queue.letters[data->queue.head] = letter;
		data->queue.head = (data->queue.head + 1) % MAX_SIZE;
		sem_post(&data->lock);

		sem_post(&data->fill);
	}
}

void semaphore_init(sem_t* sem, int def) {
	if(sem_init(sem, 1, def) != 0) {
		perror("sem_init");
		exit(1);
	}
}

struct Data* data_new() {
	struct Data* data = mmap(NULL, sizeof(struct Data), PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANON, -1, 0);
	memset(data, 0, sizeof(struct Data));
	semaphore_init(&data->lock, 1);
	semaphore_init(&data->fill, 0);
	semaphore_init(&data->empty, MAX_SIZE);
	data->queue.head = 0;
	data->queue.tail = 0;

	return data;
}

int main() {
	struct Data *data = data_new();

	for(int i = 0; i < PRODUCERS; i++) {
		if(!fork()) {
			producer(data, i);
			exit(0);
		}
	}


	char letter;
	int remaining = PRODUCERS * PRODUCTS;
	while(remaining--) {
		usleep(rand() % 500000);
		sem_wait(&data->fill);

		sem_wait(&data->lock);
		letter = data->queue.letters[data->queue.tail];
		data->queue.tail = (data->queue.tail + 1) % MAX_SIZE;
		sem_post(&data->lock);

		sem_post(&data->empty);

		printf("Consuming %c %d %d\n", letter, data->queue.head, data->queue.tail);
		usleep(100);
	}


}
