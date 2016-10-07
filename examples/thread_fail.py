import threading
import time

f = None

def fn():
    while f is None:
        pass
    f.write("another")
    f.flush()

t = threading.Thread(target=fn)
t.start()


time.sleep(0.5)

f = open("/tmp/file", "w")
f.write("test")
f.flush()


t.join()


