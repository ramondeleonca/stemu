import subprocess as sp
import socket

def find_free_port():
    """Determines a free port using sockets and closes the socket."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))  # Bind to a free port provided by the host.
        return s.getsockname()[1]  # Return the port number assigned.


def main():
    PORT = find_free_port()
    fe = sp.Popen(f"npx vite dev --port {PORT}", cwd="frontend", shell=True)
    sp.Popen(f"py main.py --dev --port {PORT}", shell=True).wait()
    fe.kill()

if __name__ == "__main__":
    main()