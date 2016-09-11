import socket
import os, os.path
import time
from struct import unpack
import logging
logging.basicConfig(level=logging.DEBUG)

sockfile = "/tmp/a"

if os.path.exists( sockfile ):
  os.remove( sockfile )

print( "Opening socket...")

server = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM )
server.bind(sockfile)
server.listen(5)

print("Listening...")
while True:
  conn, addr = server.accept()

  print('accepted connection')

  i = 0
  data = b""
  pid = None
  action = None
  params = {}
  while True:
    data += conn.recv( 1024 )
    if not data:
        break
    else:
        if pid is None:
            if len(data) >= 4:
                pid = unpack("i", data[0:4])[0]
                data = data[5:]
                logging.info("identified as PID:%d" % pid)
        else:
            if action is None:
                action = data[0]
                data = data[1:]
                logging.info("received action %d" % action)
                params = {}
            else:
                if action == 0:
                    if "fd" not in params:
                        if len(data) >= 4:
                            params["fd"] = unpack("i", data[0:4])[0]
                            logging.info("received fd %d" % params['fd'])
                            data = data[5:]
                    elif "size" not in params:
                        if len(data) >= 4:
                            params["size"] = unpack("i", data[0:4])[0]
                            logging.info("received size %d" % params['size'])
                    else:
                        if len(data) >= params['size']:
                            print(data[0:params['size']].decode('utf-8'))
                            data = data[params['size']+1:]
                            action = None
                            params = {}



        i+=1
print( "-" * 20)
print( "Shutting down...")

server.close()
os.remove( sockfile )

