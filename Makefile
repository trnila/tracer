all:
	make -C examples
	make -C backtrace

clean:
	make -C examples clean
	make -C backtrace clean
	python setup.py clean
