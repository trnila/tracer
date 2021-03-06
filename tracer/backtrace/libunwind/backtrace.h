#include <vector>
#include <stdexcept>

class BacktraceException: public std::runtime_error {
public:
    BacktraceException(std::string str): std::runtime_error(str) {}
};

void init();
std::vector<long> get_backtrace(int pid);
void destroy_pid(int pid);
void destroy();