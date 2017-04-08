import os

file_name = "/tmp/file"


def clean():
    try:
        os.unlink(file_name)
    except OSError:
        pass


clean()

with open(file_name, "w") as f:
    f.write("first")

with open(file_name, "r") as f:
    f.read()

with open(file_name, "a") as f:
    f.write("second")

with open(file_name) as f:
    f.read()


clean()
