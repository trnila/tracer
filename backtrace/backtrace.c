#include <unwind.h>
#include <errno.h>
#include <libunwind-ptrace.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ptrace.h>
#include <sys/wait.h>

#define panic(args...) do { fprintf (stderr, args); ++nerrors; } while (0)

static const int nerrors_max = 100;
int nerrors;
long data[100];
static unw_addr_space_t as;
static struct UPT_info *ui;

void do_backtrace(long *x) {
	unw_word_t ip, sp, start_ip = 0, off;
	int n = 0, ret;
	unw_cursor_t c;

	ret = unw_init_remote(&c, as, ui);
	if (ret < 0) {
		panic("unw_init_remote() failed: ret=%d\n", ret);
	}

	do {
		if ((ret = unw_get_reg (&c, UNW_REG_IP, &ip)) < 0 || (ret = unw_get_reg (&c, UNW_REG_SP, &sp)) < 0) {
			panic("unw_get_reg/unw_get_proc_name() failed: ret=%d\n", ret);
		}

		if (n == 0) {
			start_ip = ip;
		}

		x[n] = (long) ip;

		ret = unw_step(&c);
		if (ret < 0) {
			unw_get_reg(&c, UNW_REG_IP, &ip);
			panic("FAILURE: unw_step() returned %d for ip=%lx (start ip=%lx)\n", ret, (long) ip, (long) start_ip);
		}

		if (++n > 64) {
			/* guard against bad unwind info in old libraries... */
			panic("too deeply nested---assuming bogus unwind (start ip=%lx)\n", (long) start_ip);
			break;
		}

		if(nerrors > nerrors_max) {
			panic("Too many errors (%d)!\n", nerrors);
			break;
		}
	}
	while (ret > 0);

	x[n] = 0;

	if (ret < 0) {
		panic("unwind failed with ret=%d\n", ret);
	}
}


long* init(int pid) {
	as = unw_create_addr_space(&_UPT_accessors, 0);
	if (!as) {
		panic("unw_create_addr_space() failed");
	}

	ui = _UPT_create(pid);
	do_backtrace(data);

	_UPT_destroy (ui);
	unw_destroy_addr_space(as);

	return data;
}