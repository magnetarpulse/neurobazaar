import zmq
import secrets
import string

def generate_hard_to_guess_string(length=64):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

context = zmq.Context()
socket = context.socket(zmq.PUSH)

# Change the port number to the one used by the server. The server example uses port 8082.
socket.connect("tcp://localhost:8082")
auth_key = generate_hard_to_guess_string()
socket.send_string(auth_key)
socket.close()

context.term()