r"""server is a module that enables using python through a web-server.

This module can be used as the entry point to the application. In that case, it
sets up a web-server.
web-pages are determines by the command line arguments passed in.
Use "--help" to list the supported arguments.

"""

import argparse
import asyncio
import logging

from wslink import websocket as wsl
from wslink import backends

ws_server = None

# =============================================================================
# Parse a comma separated list of IP addresses
# =============================================================================

def parse_ip_list(ip_list_str):
    return ip_list_str.split(',')

# =============================================================================
# Setup default arguments to be parsed
#   --nosignalhandlers
#   --debug
#   --host               localhost
#   -p, --port           8080
#   --timeout            300 (seconds)
#   --content            '/www'  (No content means WebSocket only)
#   --authKey            vtkweb-secret
#   --auth_key           client authentication key
#   --username           username for primary client registration and authentication
#   --password           password for primary client registration and authentication
#   --client_ip          client IP address for primary client registration and authentication
#   --allowed_ips        allowed IP addresses for other client authentication
# =============================================================================

def add_arguments(parser):
    """
    Add arguments known to this module. parser must be
    argparse.ArgumentParser instance.
    """

    parser.add_argument(
        "--debug", help="log debugging messages to stdout", action="store_true"
    )
    parser.add_argument(
        "--nosignalhandlers",
        help="Prevent installation of signal handlers so server can be started inside a thread.",
        action="store_true",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="the interface for the web-server to listen on (default: 0.0.0.0)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="port number for the web-server to listen on (default: 8080)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="timeout for reaping process on idle in seconds (default: 300s, 0 to disable)",
    )
    parser.add_argument(
        "--content",
        default="",
        help="root for web-pages to serve (default: none)",
    )
    parser.add_argument(
        "--authKey",
        default="wslink-secret",
        help="Authentication key for clients to connect to the WebSocket.",
    )
    parser.add_argument(
        "--auth_key",
        type=str,
        default="",
        help="Authentication key to verify clients connecting to trame server.",
    )
    parser.add_argument(
        "--username",
        type=str,
        default="",
        help="Username for primary client registration and authentication.",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="",
        help="Password for primary client registration and authentication.",
    )
    parser.add_argument(
        "--client_ip",
        type=str,
        default="",
        help="Client IP address for primary client registration and authentication.",
    )
    parser.add_argument(
        "--allowed_ips",
        type=parse_ip_list,
        default="",
        help="Comma-separated list of allowed IP addresses for other clients authentication.",
    )
    parser.add_argument(
        "--ws-endpoint",
        type=str,
        default="ws",
        dest="ws",
        help="Specify WebSocket endpoint. (e.g. foo/bar/ws, Default: ws)",
    )
    parser.add_argument(
        "--no-ws-endpoint",
        action="store_true",
        dest="nows",
        help="If provided, disables the websocket endpoint",
    )
    parser.add_argument(
        "--fs-endpoints",
        default="",
        dest="fsEndpoints",
        help="add another fs location to a specific endpoint (i.e: data=/Users/seb/Download|images=/Users/seb/Pictures)",
    )
    parser.add_argument(
        "--reverse-url",
        dest="reverse_url",
        help="Make the server act as a client to connect to a ws relay",
    )
    parser.add_argument(
        "--ssl",
        type=str,
        default="",
        dest="ssl",
        help="add a tuple file [certificate, key] (i.e: --ssl 'certificate,key') or adhoc string to generate temporary certificate (i.e: --ssl 'adhoc')",
    )

    return parser

# =============================================================================
# Parse arguments and start webserver
# =============================================================================

def start(argv=None, protocol=wsl.ServerProtocol, description="wslink web-server"):
    """
    Sets up the web-server using with __name__ == '__main__'. This can also be
    called directly. Pass the optional protocol to override the protocol used.
    Default is ServerProtocol.
    """
    parser = argparse.ArgumentParser(description=description)
    add_arguments(parser)
    args = parser.parse_args(argv)
    # configure protocol, if available
    try:
        protocol.configure(args)
    except AttributeError:
        pass

    start_webserver(options=args, protocol=protocol)

# =============================================================================
# Stop webserver
# =============================================================================

def stop_webserver():
    if ws_server:
        loop = asyncio.get_event_loop()
        return loop.create_task(ws_server.stop())
    
# =============================================================================
# Change auth key
# =============================================================================

async def set_auth_key(auth_key):
    if ws_server:
        # print("Value of auth_key (server.py): ", auth_key)
        # print("Type of auth_key (server.py): ", type(auth_key))
        result = await ws_server.set_auth_key(auth_key)
        if result is None:
            raise TypeError("ws_server.set_auth_key returned None, expected an awaitable object")
    else:
        raise ValueError("ws_server is not initialized")

# =============================================================================
# Get auth key
# =============================================================================

async def get_auth_key(username, password, client_ip):
    if ws_server:
        # print("Value of username (server.py): ", username)
        # print("Type of username (server.py): ", type(username))
        result = await ws_server.get_auth_key(username, password, client_ip)
        if result is None:
            raise TypeError("ws_server.get_auth_key returned None, expected an awaitable object")
    else:
        raise ValueError("ws_server is not initialized")

# =============================================================================
# Check username
# =============================================================================

async def check_username(username):
    if ws_server:
        # print("Value of username (server.py): ", username)
        # print("Type of username (server.py): ", type(username
        result = await ws_server.username_exists(username)
        if result is None:
            raise TypeError("ws_server.get_auth_key returned None, expected an awaitable object")
    else:
        raise ValueError("ws_server is not initialized")
    
# =============================================================================
# Get webserver port (useful when 0 is provided and a dynamic one was picked)
# =============================================================================

def get_port():
    if ws_server:
        return ws_server.get_port()
    return -1

# =============================================================================
# Given a configuration file, create and return a webserver
#
# config = {
#     "host": "0.0.0.0",
#     "port": 8081
#     "ws": {
#         "/ws": serverProtocolInstance,
#         ...
#     },
#     static_routes: {
#         '/static': .../path/to/files,
#         ...
#     },
# }
# =============================================================================

def create_webserver(server_config, backend="aiohttp"):
    return backends.create_webserver(server_config, backend=backend)

# =============================================================================
# Generate a webserver config from command line options, create a webserver,
# and start it.
# =============================================================================

def start_webserver(
    options,
    protocol=wsl.ServerProtocol,
    disableLogging=False,
    backend="aiohttp",
    exec_mode="main",
    **kwargs,
):
    """
    Starts the web-server with the given protocol. Options must be an object
    with the following members:
        options.host:        the interface for the web-server to listen on.
        options.port:        port number for the web-server to listen on.
        options.timeout:     timeout for reaping process on idle in seconds.
        options.content:     root for web-pages to serve.
        options.auth_key:    authentication key for clients to connect to the trame server.
        options.username:    username for primary client registration and authentication.
        options.password:    password for primary client registration and authentication.
        options.client_ip:   client IP address for primary client registration and authentication.
        options.allowed_ips: allowed IP addresses for other client authentication.
    """
    global ws_server

    # Create default or custom ServerProtocol
    wslinkServer = protocol()

    if disableLogging:
        logging_level = None
    elif options.debug:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.ERROR

    if options.reverse_url:
        server_config = {
            "reverse_url": options.reverse_url,
            "ws_protocol": wslinkServer,
            "logging_level": logging_level,
        }
    else:
        server_config = {
            "host": options.host,
            "port": options.port,
            "timeout": options.timeout,
            "logging_level": logging_level,
            "auth_key": options.auth_key,
            "username": options.username,
            "password": options.password,
            "client_ip": options.client_ip,
            "allowed_ips": options.allowed_ips,
        }

        # Configure websocket endpoint
        if not options.nows:
            server_config["ws"] = {}
            server_config["ws"][options.ws] = wslinkServer

        # Configure default static route if --content requested
        if len(options.content) > 0:
            server_config["static"] = {}
            # Static HTTP + WebSocket
            server_config["static"]["/"] = options.content

        # Configure any other static routes
        if len(options.fsEndpoints) > 3:
            if "static" not in server_config:
                server_config["static"] = {}

            for fsResourceInfo in options.fsEndpoints.split("|"):
                infoSplit = fsResourceInfo.split("=")
                server_config["static"][infoSplit[0]] = infoSplit[1]

        # Confifugre SSL
        if len(options.ssl) > 0:
            from .ssl_context import generate_ssl_pair, ssl

            if options.ssl == "adhoc":
                options.ssl = generate_ssl_pair(server_config["host"])
            else:
                tokens = options.ssl.split(",")
                if len(tokens) != 2:
                    raise Exception(
                        f'ssl configure must be "adhoc" or a tuple of files "cert,key"'
                    )
                options.ssl = tokens
            cert, key = options.ssl
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server_config["ssl"] = context

        server_config["handle_signals"] = not options.nosignalhandlers

    # print(f"Starting webserver with config: {server_config}")

    # Create the webserver and start it
    ws_server = create_webserver(server_config, backend=backend)

    # Register user
    print("Registering user...")
    ws_server.register_user(options.username, options.password, options.client_ip)
    print("User registered")

    # Once we have python 3.7 minimum, we can start the server with asyncio.run()
    # asyncio.run(ws_server.start())

    # Until then, we can start the server this way
    loop = asyncio.get_event_loop()

    port_callback = None
    if hasattr(wslinkServer, "port_callback"):
        port_callback = wslinkServer.port_callback

    if hasattr(wslinkServer, "set_server"):
        wslinkServer.set_server(ws_server)

    def create_coroutine():
        return ws_server.start(port_callback)

    def main_exec():
        # Block until webapp exits
        try:
            loop.run_until_complete(create_coroutine())
        except SystemExit:
            # backend gracefully exit (due to timeout or SIGINT/SIGTERM)
            pass

    def task_exec():
        return loop.create_task(create_coroutine())

    exec_modes = {
        "main": main_exec,
        "task": task_exec,
        "coroutine": create_coroutine,
    }

    if exec_mode not in exec_modes:
        raise Exception(f"Unknown exec_mode: {exec_mode}")

    return exec_modes[exec_mode]()


if __name__ == "__main__":
    start()