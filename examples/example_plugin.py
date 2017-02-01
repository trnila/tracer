from tracer.tracer import Tracer

t = Tracer()


@t.register_handler("open")
def myopen(syscall):
    print("File {0} opened!".format(syscall.arguments[0].text))

t.main()