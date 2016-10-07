import threading

f = open("/tmp/file", "w")

def fn():
    f.write("thread")
    f.flush()
    f.close()

f.write("process")
f.flush()
t = threading.Thread(target=fn)
t.start()
t.join()

f.close()
