import zmq

context = zmq.Context()
socket = context.socket(zmq.PUSH)

# Change the port number to the one used by the server. The server example uses port 8082.
socket.connect("tcp://localhost:8082")
socket.send_string("New_key")
socket.close()

context.term()