#!/usr/bin/env python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
sock.bind(("127.0.0.1", 12345))

while True:
    data, addr = sock.recvfrom(128)
    print(data)
