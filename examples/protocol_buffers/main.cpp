#include <iostream>
#include <fstream>
#include "book.pb.h"

int main() {
	GOOGLE_PROTOBUF_VERIFY_VERSION;

	tutorial::Person person;
	person.set_id(15);
	person.set_name("cus");
	person.set_email("daniel@example.org");

	auto *number = person.add_phones();
	number->set_number("12345667");
	number->set_type(tutorial::Person::MOBILE);


	std::ofstream of("/tmp/result");
	person.SerializeToOstream(&of);

	return 1;
}
