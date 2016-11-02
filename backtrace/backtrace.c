#include <unwind.h>
#include <errno.h>
#include <fcntl.h>
#include <libunwind-ptrace.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <sys/ptrace.h>
#include <sys/wait.h>



extern char **environ;

static const int nerrors_max = 100;

int nerrors;
int verbose;
int print_names = 1;

int backtrace[10];

#define printf(...)

enum
{
	INSTRUCTION,
	SYSCALL,
	TRIGGER
}
trace_mode = SYSCALL;

#define panic(args...)						\
	do { fprintf (stderr, args); ++nerrors; } while (0)

static unw_addr_space_t as;
static struct UPT_info *ui;

static int killed;

	void
do_backtrace (long *x)
{
	unw_word_t ip, sp, start_ip = 0, off;
	int n = 0, ret;
	unw_proc_info_t pi;
	unw_cursor_t c;
	char buf[512];
	size_t len;

	ret = unw_init_remote (&c, as, ui);
	if (ret < 0)
		panic ("unw_init_remote() failed: ret=%d\n", ret);

	int i = 0;
	do
	{
		if ((ret = unw_get_reg (&c, UNW_REG_IP, &ip)) < 0
				|| (ret = unw_get_reg (&c, UNW_REG_SP, &sp)) < 0)
			panic ("unw_get_reg/unw_get_proc_name() failed: ret=%d\n", ret);

		if (n == 0)
			start_ip = ip;

		buf[0] = '\0';
		if (print_names)
			unw_get_proc_name (&c, buf, sizeof (buf), &off);

		if (verbose)
		{
			if (off)
			{
				len = strlen (buf);
				if (len >= sizeof (buf) - 32)
					len = sizeof (buf) - 32;
				sprintf (buf + len, "+0x%lx", (unsigned long) off);
			}
			printf(">>>%d\n", i);
			printf ("%016lx %-32s (sp=%016lx)\n", (long) ip, buf, (long) sp);
			//backtrace[i] = (long) ip;
			//backtrace[0] = 5;
			x[i] = (long) ip;
			i++;

		}

		if ((ret = unw_get_proc_info (&c, &pi)) < 0)
			panic ("unw_get_proc_info(ip=0x%lx) failed: ret=%d\n", (long) ip, ret);
		else if (verbose)
			printf ("\tproc=%016lx-%016lx\n\thandler=%lx lsda=%lx",
					(long) pi.start_ip, (long) pi.end_ip,
					(long) pi.handler, (long) pi.lsda);

#if UNW_TARGET_IA64
		{
			unw_word_t bsp;

			if ((ret = unw_get_reg (&c, UNW_IA64_BSP, &bsp)) < 0)
				panic ("unw_get_reg() failed: ret=%d\n", ret);
			else if (verbose)
				printf (" bsp=%lx", bsp);
		}
#endif
		if (verbose)
			printf ("\n");

		ret = unw_step (&c);
		if (ret < 0)
		{
			unw_get_reg (&c, UNW_REG_IP, &ip);
			panic ("FAILURE: unw_step() returned %d for ip=%lx (start ip=%lx)\n",
					ret, (long) ip, (long) start_ip);
		}

		if (++n > 64)
		{
			/* guard against bad unwind info in old libraries... */
			panic ("too deeply nested---assuming bogus unwind (start ip=%lx)\n",
					(long) start_ip);
			break;
		}
		if (nerrors > nerrors_max)
		{
			panic ("Too many errors (%d)!\n", nerrors);
			break;
		}
	}
	while (ret > 0);
	x[i] = 0;

	if (ret < 0)
		panic ("unwind failed with ret=%d\n", ret);

	if (verbose)
		printf ("================\n\n");
}

static pid_t target_pid;


long data[100];
long* init(int p) {
	target_pid = p;
	int status, pid, pending_sig, optind = 1, state = 1;
	verbose = 1;

	as = unw_create_addr_space (&_UPT_accessors, 0);
	if (!as)
		panic ("unw_create_addr_space() failed");

	printf("backtracing %d\n", target_pid);



	ui = _UPT_create (target_pid);
	printf("before backtrace\n");
	do_backtrace(data);

	fflush(stdout);

	_UPT_destroy (ui);
	unw_destroy_addr_space(as);

	return data;
}


	
