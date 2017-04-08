import threading


def thread1():
    print("Thread 1")


print("Program")
t1 = threading.Thread(target=thread1)
t1.start()
t1.join()
