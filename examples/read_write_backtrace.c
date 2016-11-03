#include <stdio.h>

void save_settings() {
	FILE *f = fopen("/tmp/file", "w");
	if(!f) {
		perror("fopen:");
	}
	fprintf(f, "Hello!");
	fprintf(f, " World!");
	fclose(f);
}

void load_settings() {
	FILE *f = fopen("/tmp/file", "r");
	if(!f) {
		perror("fopen:");
	}

	char word[200];
	fscanf(f, "%s", word);
	printf("%s\n", word);
	fscanf(f, "%s", word);
	printf("%s\n", word);
	fflush(stdout);
	fclose(f);
}

void default_settings() {
	save_settings();
}

void init_system() {
	default_settings();
	load_settings();
}


void main() {
	init_system();
}