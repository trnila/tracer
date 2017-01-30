all:
	make -C examples

clean:
	make -C examples clean
	python setup.py clean
