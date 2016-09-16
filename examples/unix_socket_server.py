import socket
import os, os.path

sockfile = "/tmp/reverse.sock"

if os.path.exists(sockfile):
    os.remove(sockfile)

server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(sockfile)
server.listen(5)

print("started")
conn, addr = server.accept()
while True:
    data = conn.recv(1024)
    if not data:
        break

    conn.send(data[::-1])
    break

server.close()
os.remove(sockfile)
