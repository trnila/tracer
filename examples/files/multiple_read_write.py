file = "/tmp/file"

def clean():
    #os.unlink(file)
    pass

clean()

with open(file, "w") as f:
    f.write("first")


with open(file, "r") as f:
    f.read()

with open(file, "a") as f:
    f.write("second")

with open(file) as f:
    f.read()


clean()
