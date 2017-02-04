#include <libunwind-ptrace.h>
#include <unordered_map>
#include "backtrace.h"
#include "utils.h"

unw_addr_space_t as;
std::unordered_map<int, struct UPT_info*> unwind_info;

void init() {
    as = unw_create_addr_space(&_UPT_accessors, 0);
    if(!as) {
        throw BacktraceException("unw_create_addr_space() failed");
    }
}

std::vector<long> do_backtrace(struct UPT_info *ui) {
    std::vector<long> backtrace;

	unw_word_t ip, sp, start_ip = 0, off;
	int n = 0, ret;
	unw_cursor_t c;

	ret = unw_init_remote(&c, as, ui);
	if (ret < 0) {
		throw BacktraceException(Formatter() << "unw_init_remote() failed: ret=" << ret);
	}

	do {
		if ((ret = unw_get_reg (&c, UNW_REG_IP, &ip)) < 0 || (ret = unw_get_reg (&c, UNW_REG_SP, &sp)) < 0) {
			throw BacktraceException(Formatter() << "unw_get_reg/unw_get_proc_name() failed: ret=" << ret);
		}

		if (n == 0) {
			start_ip = ip;
		}

        backtrace.push_back(ip);

		ret = unw_step(&c);
		if (ret < 0) {
			unw_get_reg(&c, UNW_REG_IP, &ip);
			throw BacktraceException(
			    Formatter() << "unw_step() returned " << ret
			                << " for ip=0x" << std::hex << ip
			                << " (start ip=0x" << start_ip << ")"
			);
		}

		if (++n > 64) {
			/* guard against bad unwind info in old libraries... */
			throw BacktraceException(Formatter() << "too deeply nested---assuming bogus unwind (start ip=0x" << start_ip << ")");
		}
	}
	while (ret > 0);

	if (ret < 0) {
		throw BacktraceException(Formatter() << "unwind failed with ret=" << ret);
	}

	return backtrace;
}

void destroy_pid(int pid) {
    auto it = unwind_info.find(pid);

    if(it != unwind_info.end()) {
        _UPT_destroy(it->second);
        unwind_info.erase(it);
    }
}

void destroy() {
    for(auto it: unwind_info) {
        destroy_pid(it.first);
    }

    //if(as) {
        unw_destroy_addr_space(as);
        as = nullptr;
    //}
}

std::vector<long> get_backtrace(int pid) {
    auto it = unwind_info.find(pid);
    if(it == unwind_info.end()) {
        struct UPT_info *ui = (UPT_info*) _UPT_create(pid);
        it = unwind_info.insert(std::make_pair(pid, ui)).first;
    }

    return do_backtrace(it->second);
}