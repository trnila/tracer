#include <sstream>

class Formatter {
public:
    template<typename T>
    Formatter& operator<<(const T &type) {
        os << type;
        return *this;
    }

    operator std::string() {
        return os.str();
    }
private:
    std::ostringstream os;
};