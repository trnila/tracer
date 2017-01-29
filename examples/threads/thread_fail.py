import threading

f = None
lock = threading.Lock()

def fn():
    lock.acquire()
    f.write("another")
    f.flush()
    lock.release()

lock.acquire()

t = threading.Thread(target=fn)
t.start()
f = open("/tmp/file", "w")
f.write("test")
f.flush()
lock.release()


t.join()


