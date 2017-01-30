#include <unwind.h>
#include <errno.h>
#include <libunwind-ptrace.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <string>
#include <unordered_map>
#include "backtrace.h"
#include "utils.h"


long data[100];
unw_addr_space_t as;
std::unordered_map<int, struct UPT_info*> unwind_info;

void do_backtrace(long *x, struct UPT_info *ui) {
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

		x[n] = (long) ip;

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

	x[n] = 0;

	if (ret < 0) {
		throw BacktraceException(Formatter() << "unwind failed with ret=" << ret);
	}
}


void init() {
    as = unw_create_addr_space(&_UPT_accessors, 0);
    if(!as) {
        throw BacktraceException("unw_create_addr_space() failed");
    }
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

    unw_destroy_addr_space(as);
}

long* get_backtrace(int pid) {
    auto it = unwind_info.find(pid);
    if(it == unwind_info.end()) {
        struct UPT_info *ui = (UPT_info*) _UPT_create(pid);
        it = unwind_info.insert(std::make_pair(pid, ui)).first;
    }

    do_backtrace(data, it->second);
    return data;
}