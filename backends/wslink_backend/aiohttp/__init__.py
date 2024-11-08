# Importing necessary modules for
# {
#   - future annotations
#   - system operations
#   - logging
#   - unique identifiers
#   - JSON handling
#   - file path manipulations
# }
from __future__ import annotations
import os
import logging
import sys
import uuid
import json
from pathlib import Path

# Core backend specific imports
from wslink.protocol import WslinkHandler, AbstractWebApp
import aiohttp
import aiohttp.web as aiohttp_web

# HTTPS simulation
from wslink.ssl_context import load_ssl_context, generate_ssl_pair

# Authentication imports
import base64
import hmac
import secrets
import hashlib

# Other imports
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import asyncio

# 4MB is the default inside aiohttp
MSG_OVERHEAD = int(os.environ.get("WSLINK_MSG_OVERHEAD", 4096))
MAX_MSG_SIZE = int(os.environ.get("WSLINK_MAX_MSG_SIZE", 4194304))
HEART_BEAT = int(os.environ.get("WSLINK_HEART_BEAT", 30))  # 30 seconds
HTTP_HEADERS: str | None = os.environ.get("WSLINK_HTTP_HEADERS")  # path to json file

if HTTP_HEADERS and Path(HTTP_HEADERS).exists():
    HTTP_HEADERS: dict = json.loads(Path(HTTP_HEADERS).read_text())

# -----------------------------------------------------------------------------
# Logger configuration
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)

# -----------------------------------------------------------------------------
# Dataclass that stores information about the user credentials and verification
# -----------------------------------------------------------------------------

@dataclass
class UserCredentials:
    username: str
    client_ip: str
    password_hash: str
    salt: bytes
    last_verified: datetime
    failed_attempts: int = 0

# -----------------------------------------------------------------------------
# Class that verifies the identity of a user based on the username and password
# -----------------------------------------------------------------------------

class IdentityVerifier:
    def __init__(self, max_attempts: int = 3):
        self._credentials: dict[str, UserCredentials] = {}
        self._max_attempts = max_attempts
        self.security_logger = SecurityLogger()
    
    def register_user(self, username: str, password: str, ip_address: str) -> None:
        """Register a new user with hashed password and IP address"""
        
        # print(f"Registering new user: {username}")
        logger.info(f"Registering new user: {username}")

        # Generate a random salt for each user
        salt = os.urandom(16)  # 16 bytes salt
        # print(f"Salt generated for user {username}: {salt}")
        logger.info(f"Salt generated for user {username}: {salt}")
        
        # Hash the password using a secure method
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',            # Hashing algorithm
            password.encode(),   # Convert password to bytes
            salt,                # Random salt
            100000               # Number of iterations
        ).hex()                  # Convert to hexadecimal
        
        # Store the user credentials
        self._credentials[username] = UserCredentials(
            username=username,
            password_hash=password_hash,
            salt=salt,
            client_ip=ip_address,
            last_verified=datetime.now()
        )
        
        # Log the registration event
        self.security_logger.log_event(SecurityEvent(
            timestamp=datetime.now().isoformat(),
            event_type="USER_REGISTRATION",
            ip_address=ip_address,  # Use the provided IP address
            status="SUCCESS",
            details=f"New user registered: {username}"
        ))
    
    def verify_identity(self, username: str, password: str, client_ip: str) -> Tuple[bool, str]:
        """
        Verify user identity based on username, password and client IP address
        Returns (success, message)
        """
        
        print(f"Verifying identity for user: {username}")
        logger.info(f"Verifying identity for user: {username}")
        
        # Check if user exists
        if username not in self._credentials:
            self.security_logger.log_event(SecurityEvent(
                timestamp=datetime.now().isoformat(),
                event_type="FAILED_LOGIN",
                ip_address=client_ip,
                status="FAILURE",
                details=f"Unknown username: {username}"
            ))
            return False, "Invalid username"
        
        user = self._credentials[username]

        # Check if the IP address matches
        if user.client_ip != client_ip:
            self.security_logger.log_event(SecurityEvent(
                timestamp=datetime.now().isoformat(),
                event_type="FAILED_LOGIN",
                ip_address=client_ip,
                status="FAILURE",
                details=f"IP address mismatch for user: {username}"
            ))
            return False, "IP address mismatch"
        
        # Check if user has exceeded maximum attempts
        if user.failed_attempts >= self._max_attempts:
            self.security_logger.log_event(SecurityEvent(
                timestamp=datetime.now().isoformat(),
                event_type="ACCOUNT_LOCKED",
                ip_address=client_ip,
                status="LOCKED",
                details=f"Account locked due to too many failed attempts: {username}"
            ))
            return False, "Account locked due to too many failed attempts"
        
        # Get the hashed password and salt
        attempted_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            user.salt,
            100000
        ).hex()
        
        # Verify the password hash
        if not hmac.compare_digest(attempted_hash.encode(), user.password_hash.encode()):
            user.failed_attempts += 1
            self.security_logger.log_event(SecurityEvent(
                timestamp=datetime.now().isoformat(),
                event_type="FAILED_LOGIN",
                ip_address=client_ip,
                status="FAILURE",
                details=f"Invalid password for user: {username}"
            ))
            return False, "Invalid password"
        
        # Success - reset failed attempts and update last verified time
        user.failed_attempts = 0
        user.last_verified = datetime.now()
        
        self.security_logger.log_event(SecurityEvent(
            timestamp=datetime.now().isoformat(),
            event_type="SUCCESSFUL_LOGIN",
            ip_address=client_ip,
            status="SUCCESS",
            details=f"Successful login for user: {username}"
        ))
        
        return True, "Identity verified successfully"

# -----------------------------------------------------------------------------
# Dataclass that stores information about a security event for logging purposes
# -----------------------------------------------------------------------------

@dataclass
class SecurityEvent:
    timestamp: str
    event_type: str
    ip_address: str
    status: str
    details: str
    session_id: Optional[str] = None
    user_agent: Optional[str] = None

# -----------------------------------------------------------------------------
# Class that logs security event(s) and the detail(s) to log file with rotation
# -----------------------------------------------------------------------------

class SecurityLogger:
    def __init__(self, log_file: str = "security.log"):
        self.logger = logging.getLogger("security")
        self.logger.setLevel(logging.INFO)
        
        # File handler with rotation
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_event(self, event: SecurityEvent) -> None:
        self.logger.info(
            f"Type: {event.event_type}, "
            f"IP: {event.ip_address}, "
            f"Status: {event.status}, "
            f"Details: {event.details}"
            + (f", Session: {event.session_id}" if event.session_id else "")
        )

# -----------------------------------------------------------------------------
# Dataclass that stores information about a IP address and it attempts to login
# -----------------------------------------------------------------------------

@dataclass
class IPAttemptInfo:
    failed_attempts: int
    first_attempt_time: datetime
    ban_start_time: datetime | None = None

# -----------------------------------------------------------------------------
# Class that manages rate limiting for failed login attempts from an IP address
# -----------------------------------------------------------------------------

class IPRateLimiter:
    def __init__(self, max_attempts: int = 5, ban_duration_hours: int = 24, attempt_window_minutes: int = 60):
        self._ip_attempts: Dict[str, IPAttemptInfo] = {}
        self._max_attempts = max_attempts
        self._ban_duration = timedelta(hours=ban_duration_hours)
        self._attempt_window = timedelta(minutes=attempt_window_minutes)
    
    def is_ip_banned(self, ip_address: str) -> bool:
        """Check if an IP is currently banned"""

        if ip_address not in self._ip_attempts:
            return False
            
        ip_info = self._ip_attempts[ip_address]
        if ip_info.ban_start_time is None:
            return False
            
        # Check if ban period has expired
        if datetime.now() - ip_info.ban_start_time > self._ban_duration:
            # Remove expired ban
            del self._ip_attempts[ip_address]
            return False
            
        return True
    
    def record_failed_attempt(self, ip_address: str) -> bool:
        """
        Record a failed attempt for an IP address
        Returns True if the IP should be banned
        """

        now = datetime.now()
        
        if ip_address not in self._ip_attempts:
            self._ip_attempts[ip_address] = IPAttemptInfo(
                failed_attempts=1,
                first_attempt_time=now
            )
            return False
        
        ip_info = self._ip_attempts[ip_address]
        
        # Reset attempts if outside the attempt window
        if now - ip_info.first_attempt_time > self._attempt_window:
            ip_info.failed_attempts = 1
            ip_info.first_attempt_time = now
            return False
        
        # Increment attempts
        ip_info.failed_attempts += 1
        
        # Check if should be banned
        if ip_info.failed_attempts >= self._max_attempts:
            ip_info.ban_start_time = now
            return True
            
        return False
    
    def clear_attempts(self, ip_address: str) -> None:
        """Clear attempts for an IP address on successful authentication"""

        if ip_address in self._ip_attempts:
            del self._ip_attempts[ip_address]

# -----------------------------------------------------------------------------
# Dataclass that store information about a session (ID, timestamps, IP address)
# ----------------------------------------------------------------------------- 

@dataclass
class SessionInfo:
    id: str
    created_at: datetime
    last_active: datetime
    client_ip: str
    csrf_token: str

# -----------------------------------------------------------------------------
# Class to validate the key and IP address of incoming requests from the client
# -----------------------------------------------------------------------------

class AuthenticationManager:
    """Manages authentication state for a WebAppServer instance"""
    
    def __init__(self, initial_key: str, session_timeout_minutes: int = 30):
        self._auth_key = initial_key
        self._sessions: Dict[str, SessionInfo] = {}
        self._session_timeout = timedelta(minutes=session_timeout_minutes)
        self._blacklisted_tokens = set()
        self._rate_limiter = IPRateLimiter()
        self.security_logger = SecurityLogger()
        self._identity_verifier = IdentityVerifier()

    def create_session(self, client_ip: str) -> Tuple[str, str]:
        """Create a new session with CSRF token"""

        print("Creating new session...")
        logger.info("Creating new session...")
        session_id = str(uuid.uuid4())
        csrf_token = secrets.token_urlsafe(32)  # Generate secure CSRF token
        now = datetime.now()
        
        self._sessions[session_id] = SessionInfo(
            id=session_id,
            created_at=now,
            last_active=now,
            client_ip=client_ip,
            csrf_token=csrf_token
        )
        
        self.security_logger.log_event(SecurityEvent(
            timestamp=now.isoformat(),
            event_type="SESSION_CREATED",
            ip_address=client_ip,
            status="SUCCESS",
            details="New session created",
            session_id=session_id
        ))
        
        return session_id, csrf_token
    
    def validate_key(self, provided_key: str, client_ip: str) -> bool:
        """Validate key using constant-time comparison"""

        try:
            decoded_key = base64.urlsafe_b64decode(provided_key.encode()).decode()
            # Use constant-time comparison to prevent timing attacks
            is_valid = hmac.compare_digest(
                decoded_key.encode(),
                self._auth_key.encode()
            )
            
            self.security_logger.log_event(SecurityEvent(
                timestamp=datetime.now().isoformat(),
                event_type="AUTH_ATTEMPT",
                ip_address=client_ip,
                status="SUCCESS" if is_valid else "FAILURE",
                details="Key validation attempt"
            ))
            
            return is_valid
        except Exception as e:
            self.security_logger.log_event(SecurityEvent(
                timestamp=datetime.now().isoformat(),
                event_type="AUTH_ERROR",
                ip_address=client_ip,
                status="ERROR",
                details=f"Key validation error: {str(e)}"
            ))
            return False

    def validate_csrf_token(self, session_id: str, csrf_token: str) -> bool:
        """Validate CSRF token for a session"""

        session = self._sessions.get(session_id)
        if not session:
            return False
        return hmac.compare_digest(
            session.csrf_token.encode(),
            csrf_token.encode()
        )
    
    def validate_session(self, session_id: str, client_ip: str) -> bool:
        """Validate session with IP binding and timeout checks"""

        if session_id in self._blacklisted_tokens:
            return False
            
        session = self._sessions.get(session_id)
        if not session:
            return False
            
        # Verify client IP matches the original IP
        if session.client_ip != client_ip:
            self.invalidate_session(session_id)
            return False
            
        # Check if session has expired
        if datetime.now() - session.last_active > self._session_timeout:
            self.invalidate_session(session_id)
            return False
            
        # Update last active timestamp
        session.last_active = datetime.now()
        return True

    def invalidate_session(self, session_id: str) -> None:
        """Invalidate a session and add its token to blacklist"""

        if session_id in self._sessions:
            self._blacklisted_tokens.add(session_id)
            del self._sessions[session_id]
    
    def set_auth_key(self, new_key: str) -> None:
        """Update the authentication key"""

        self._auth_key = new_key
        print(f"New authentication key set: {new_key}")
        logger.info(f"New authentication key set: {new_key}")

        # Clear all sessions when key is updated
        self.clear_all_sessions()
    
    def get_auth_key(self, username: str, password: str, client_ip: str) -> Optional[str]:
        """Get the current authentication key"""

        print("Verifying identity to get authentication key")
        logger.info("Verifying identity to get authentication key")

        print("Getting IP address...")
        logger.info("Getting IP address...")

        # Check if IP is banned
        if self._rate_limiter.is_ip_banned(client_ip):
            self.security_logger.log_event(SecurityEvent(
                timestamp=datetime.now().isoformat(),
                event_type="ACCESS_ATTEMPT",
                ip_address=client_ip,
                status="DENIED",
                details="Banned IP attempted access"
            ))
            print("Access denied: Attempted access from banned IP")
            logger.error("Access denied: Attempted access from banned IP")
            return None
        
        print("Got IP address:", client_ip)
        print("Submitting credentials for verification...")

        # Verify the identity of the user
        print("Verifying identity...")
        logger.info("Verifying identity...")

        success, message = self._identity_verifier.verify_identity(username, password, client_ip)

        print(f"Identity verification result: {success}, Message: {message}")

        if not success:
            # Record failed attempt, if record_failed_attempt returns True, the IP is banned
            if self._rate_limiter.record_failed_attempt(client_ip):
                self.security_logger.log_event(SecurityEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type="IP_BANNED",
                    ip_address=client_ip,
                    status="BANNED",
                    details="IP address banned due to too many failed attempts"
                ))
            return None
        
        # Clear IP rate limiting on successful authentication
        self._rate_limiter.clear_attempts(client_ip)

        print("Identity verified successfully")
        logger.info("Identity verified successfully")

        print("Auth key retrieved successfully")
        print("Current auth key:", self._auth_key)

        return self._auth_key
    
    def clear_all_sessions(self) -> None:
        """Clear all active sessions"""

        print("Clearing all active sessions...")
        logger.info("Clearing all active sessions...")
        session_count = len(self._sessions)
        print("Session count:", session_count)
        logger.info(f"Session count: {session_count}")
        print("Current sessions:", self._sessions)
        logger.info(f"Current sessions: {self._sessions}")
        self._sessions.clear()
        print(f"Cleared {session_count} active sessions")
        logger.info(f"Cleared {session_count} active sessions")
    
# -----------------------------------------------------------------------------
# Function to make sure that the path starts with a slash, example: /index.html
# -----------------------------------------------------------------------------

def _fix_path(path):
    if not path.startswith("/"):
        return "/{0}".format(path)
    return path

# -----------------------------------------------------------------------------
# Middleware function to add custom headers to the HTTP response of the web app
# -----------------------------------------------------------------------------

@aiohttp_web.middleware
async def http_headers(request: aiohttp_web.Request, handler):
    response: aiohttp_web.Response = await handler(request)
    for k, v in HTTP_HEADERS.items():
        response.headers.setdefault(k, v)

    return response

# -----------------------------------------------------------------------------
# Updated the class to only serve index.html if the key is correct in the query
# -----------------------------------------------------------------------------

class WebAppServer(AbstractWebApp):
    def __init__(self, server_config):
        AbstractWebApp.__init__(self, server_config)

        # Get the auth_key from the server_config
        # If not present in the server_config, default to "key"
        # You can choose to use this default value or raise an error
        # self.auth_key = server_config.get("auth_key", "key")  

        # If the auth_key is not present in the server_config, raise an error
        # This should not be present if the key is not provided in the server_config but there is a default value
        if "auth_key" not in server_config:
            raise ValueError("auth_key is missing in server_config (required). Hint: Look at the arguments given to the server.")
        
        # Get the auth_key from the server_config
        self.auth_key = server_config["auth_key"] 
        print("Auth_key parameter recieved:", self.auth_key)
        logger.info(f"Auth_key parameter recieved: {self.auth_key}")

        # Create base64 encoded version
        self.auth_key_b64 = base64.urlsafe_b64encode(self.auth_key.encode()).decode()
        print("Base64 encoded key:", self.auth_key_b64)
        logger.info(f"Base64 encoded key: {self.auth_key_b64}")

        # Get the session timeout from the server_config
        # If not present in the server_config, default to 30 minutes
        session_timeout = server_config.get("session_timeout_minutes", 30)
        print(f"Session timeout set to {session_timeout} minutes")
        logger.info(f"Session timeout set to {session_timeout} minutes")
        
        # Initialize the authentication manager with the key and session timeout as arguments
        self.auth_manager = AuthenticationManager(
            self.auth_key,
            session_timeout_minutes=session_timeout
        )

        # If the HTTP_HEADERS environment variable is set, add custom headers to the HTTP response
        # No custom headers will be added if the environment variable is not set/none (default)
        if HTTP_HEADERS:
            print("Adding custom headers to HTTP response")
            logger.info("Adding custom headers to HTTP response")
            self.set_app(aiohttp_web.Application(middlewares=[http_headers]))
        else:
            print("No custom headers to add to HTTP response")
            logger.info("No custom headers to add to HTTP response")
            self.set_app(aiohttp_web.Application())

        # Initialize the WebSocket handlers
        self._ws_handlers = []
        self._site = None
        self._runner = None
        self.app['state'] = {'sessions': set()}  # Store sessions in the application state

        # Checks the client IP address and the key in the query
        async def root_handler(request):
            """Handle authentication and serve the root page"""

            # Get the query parameters -> ?key=...
            query_params = request.rel_url.query
            key = query_params.get('key')

            # Get the client IP
            peername = request.transport.get_extra_info('peername')
            if peername is None:
                print("Cannot verify client IP address")
                logger.error("Cannot verify client IP address")
                return aiohttp.web.HTTPForbidden(text="Cannot verify client IP address")
            
            if peername is not None:
                # First element of peername is the client IP
                # Second element is the client port
                client_ip, _ = peername
                print(f"Client IP: {client_ip}")
                logger.info(f"Client IP: {client_ip}")

                # Check if IP is banned
                if self.auth_manager._rate_limiter.is_ip_banned(client_ip):
                    self.auth_manager.security_logger.log_event(SecurityEvent(
                        timestamp=datetime.now().isoformat(),
                        event_type="ACCESS_ATTEMPT",
                        ip_address=client_ip,
                        status="DENIED",
                        details="Banned IP attempted access"
                    ))
                    print("Access denied: IP address is temporarily banned due to too many failed attempts")
                    logger.error("Access denied: IP address is temporarily banned due to too many failed attempts")
                    return aiohttp.web.HTTPForbidden(
                        text="Access denied: IP address is temporarily banned due to too many failed attempts"
                    )

                # Only allow access from localhost or allowed IP
                # The only default allowed IP is 127.0.0.1 (localhost)
                # You can add more allowed IPs in the server_config -> server(allowed_ip="...")
                if client_ip != '127.0.0.1' and client_ip not in server_config.get('allowed_ips', []):
                    print("Access Denied: Unauthorized IP address.")
                    logger.error("Access Denied: Unauthorized IP address.")
                    return aiohttp.web.HTTPForbidden(text="Access Denied: Unauthorized IP address.")

            print(f"Received encoded key: {key}")
            logger.info(f"Received encoded key: {key}")
            print(f"Request received: {request.rel_url}")
            logger.info(f"Request received: {request.rel_url}")
            
            # Check for key in query
            if key:
                if self.auth_manager.validate_key(key, client_ip):
                    print("Authentication successful (key verified). Creating session...")
                    logger.info("Authentication successful (key verified). Creating session...")
                    session_id, csrf_token = self.auth_manager.create_session(client_ip)
                    print(f"Session ID: {session_id}, CSRF Token: {csrf_token}")
                    logger.info(f"Session ID: {session_id}, CSRF Token: {csrf_token}")

                    # Add the session ID to the application state
                    self.app['state']['sessions'].add(session_id)
                    print("Active sessions:", self.app['state']['sessions'])
                    logger.info(f"Active sessions: {self.app['state']['sessions']}")
                    
                    # Create response with CSRF token
                    print("Redirecting to index.html... with a clean URL (no key)")
                    logger.info("Redirecting to index.html... with a clean URL (no key)")
                    response = aiohttp.web.HTTPFound('/')

                    # Set cookies for session and CSRF token. Both have a max age of 30 minutes.
                    response.set_cookie(
                        'auth_session',     # Cookie name (auth_session)
                        session_id,         # Cookie value (session_id attribute)
                        httponly=True,      # Prevent client-side scripts (e.g. JavaScript) from accessing the cookie
                        secure=True,        # Only send cookie over HTTPS
                        samesite='Strict',  # Prevent cross-site request forgery
                        max_age=1800        # 30 minutes validity
                    )
                    response.set_cookie(    
                        'csrf_token',       # Cookie name (csrf_token)
                        csrf_token,         # Cookie value (csrf_token attribute)
                        httponly=False,     # Allow client-side scripts to access the cookie, since it's used for CSRF protection
                        secure=True,        # Only send cookie over HTTPS
                        samesite='Strict',  # Prevent cross-site request forgery
                        max_age=1800        # 30 minutes validity
                    )
                    return response
                else:
                    # Record failed attempt
                    should_ban = self.auth_manager._rate_limiter.record_failed_attempt(client_ip)
                    if should_ban:
                        self.auth_manager.security_logger.log_event(SecurityEvent(
                            timestamp=datetime.now().isoformat(),
                            event_type="IP_BANNED",
                            ip_address=client_ip,
                            status="BANNED",
                            details="IP banned due to too many failed attempts"
                        ))
                        print("Access denied: IP address is temporarily banned due to too many failed attempts")
                        logger.error("Access denied: IP address is temporarily banned due to too many failed attempts")
                        return aiohttp.web.HTTPForbidden(text="Access denied: Too many failed attempts. Your IP has been temporarily banned.")
                    return aiohttp.web.HTTPForbidden(text="Invalid authentication")

            # Validate existing session
            session_id = request.cookies.get('auth_session')
            if session_id and self.auth_manager.validate_session(session_id, client_ip):
                home_dir = os.path.expanduser("~")
                file_path = os.path.join(home_dir, "neurobazaar/.venv/lib/python3.11/site-packages/trame_client/module/vue2-www/index.html")
                return aiohttp.web.FileResponse(file_path)
            
            # No valid session, return forbidden
            print("Access Denied: Invalid key, expired session or missing authentication.")
            logger.error("Access Denied: Invalid key, expired session or missing authentication.")
            return aiohttp.web.HTTPForbidden(text="Access Denied: Invalid key, expired session or missing authentication.")
        
        # Add routes
        if "ws" in server_config:
            routes = []
            for route, server_protocol in server_config["ws"].items():
                protocol_handler = AioHttpWsHandler(server_protocol, self)
                self._ws_handlers.append(protocol_handler)
                routes.append(
                    aiohttp_web.get(_fix_path(route), protocol_handler.handleWsRequest)
                )
            self.app.add_routes(routes)
        
        if "static" in server_config:
            static_routes = server_config["static"]
            routes = []

            for route in sorted(static_routes.keys(), reverse=True):
                server_path = static_routes[route]
                if route != "/index.html":
                    routes.append(
                        aiohttp_web.static(
                            _fix_path(route), server_path, append_version=True
                        )
                    )

            self.app.router.add_route("GET", "/", root_handler)
            self.app.router.add_route("GET", "/index.html", root_handler)
            self.app.add_routes(routes)

    async def set_auth_key(self, new_key: str) -> None:
        """Update the authentication key and disconnect all clients"""

        print(f"Setting new auth key: {new_key}")
        logger.info(f"Setting new auth key: {new_key}")
        self.auth_key = new_key
        self.auth_key_b64 = base64.urlsafe_b64encode(new_key.encode()).decode()

        print("New base64 encoded key:", self.auth_key_b64)
        logger.info(f"New base64 encoded key: {self.auth_key_b64}")
        
        # Update the auth manager (this will clear all sessions)
        self.auth_manager.set_auth_key(new_key)
        
        # Disconnect all WebSocket clients.
        # This is different from closing the server, since clients can reconnect once they validate the new key
        for handler in self._ws_handlers:
            await handler.disconnectClients()
        
        return True
    
    def register_user(self, username: str, password: str, ip_address: str) -> None:
        """Register a new user with hashed password and IP address"""

        try:
            print(f"Registering new user: {username}")
            logger.info(f"Registering new user: {username}")

            # Register the user with the identity verifier
            self.auth_manager._identity_verifier.register_user(
                username,
                password,
                ip_address
            )

            # print("User registered successfully")
            logger.info("User registered successfully")

            return True
        except Exception as e:
            print(f"Registration failed: {e}")
            logger.error(f"Registration failed: {e}")
            raise
    
    async def get_auth_key(self, username: str, password: str, client_ip: str) -> Optional[str]:
        """Get the current authentication key"""  
        
        print("Getting authentication key...")
        logger.info("Getting authentication key...")
        return self.auth_manager.get_auth_key(username, password, client_ip)
    
    async def username_exists(self, username: str) -> bool:
        """Check if a username already exists"""

        print(f"Checking if username {username} exists...")
        logger.info(f"Checking if username {username} exists...")

        print("Username exists:", username in self.auth_manager._identity_verifier._credentials)
        return username in self.auth_manager._identity_verifier._credentials

    # -------------------------------------------------------------------------
    # Server status
    # -------------------------------------------------------------------------

    @property
    def runner(self):
        return self._runner

    @property
    def site(self):
        return self._site

    def get_port(self):
        """Return the actual port used by the server"""
        return self.runner.addresses[0][1]
    
    # -------------------------------------------------------------------------
    # Get Neurobazaar directory
    # -------------------------------------------------------------------------

    def get_neurobazaar_dir(self):
        """Get the root directory of the Neurobazaar project."""
        cwd = os.getcwd()
        index = cwd.index('neurobazaar')
        # print("CWD:", cwd[:index + len('neurobazaar')])
        return cwd[:index + len('neurobazaar')]
    
    # -------------------------------------------------------------------------
    # Get SSL certificate and private key files (paths)
    # -------------------------------------------------------------------------

    def _get_ssl_paths(self):
        """Get paths to SSL certificate and private key files."""
        key_dir = Path(self.get_neurobazaar_dir()) / '.ssl'
        return str(key_dir / 'cert.pem'), str(key_dir / 'pkey.pem')

    # -------------------------------------------------------------------------
    # Life cycles
    # -------------------------------------------------------------------------

    async def start(self, port_callback=None):
        # Get the SSL certificate and private key files
        cert_file, pkey_file = self._get_ssl_paths()

        # Check if the certificate and key files exist
        if not (os.path.exists(cert_file) and os.path.exists(pkey_file)):
            # Generate and save SSL pair if they don't exist
            logger.info("Generating new SSL certificate and private key")
            print("Generating new SSL certificate and private key")
            cert_file, pkey_file = generate_ssl_pair(self.host)
            print("Certificate file saved at:", cert_file)
            print("Private key file saved at:", pkey_file)
            logger.info(f"Certificate file saved at: {cert_file}")
            logger.info(f"Private key file saved at: {pkey_file}")
        else:
            # print("Using existing certificate file at:", cert_file)
            # print("Using existing private key file at:", pkey_file)
            # logger.info(f"Using existing certificate file at: {cert_file}")
            # logger.info(f"Using existing private key file at: {pkey_file}")
            print("Got existing certificate and private key files")

        # Load the SSL context 
        # self.ssl_context = load_ssl_context(cert_file, pkey_file)  

        self._runner = aiohttp_web.AppRunner(
            self.app, handle_signals=self.handle_signals
        )

        print("awaiting runner setup")
        logger.info("awaiting runner setup")
        await self._runner.setup()

        # Default HTTP server
        # self._site = aiohttp_web.TCPSite(
        #     self._runner, self.host, self.port, ssl_context=self.ssl_context  
        # )

        # HTTP server with SSL context (HTTPS)
        self._site = aiohttp_web.TCPSite(
            self._runner, self.host, self.port, ssl_context=load_ssl_context(cert_file, pkey_file)  
        )

        print("awaiting site startup")
        logger.info("awaiting site startup")
        await self._site.start()

        if port_callback is not None:
            port_callback(self.get_port())

        logger.info("Print WSLINK_READY_MSG")
        STARTUP_MSG = os.environ.get("WSLINK_READY_MSG", "wslink: Starting factory")
        if STARTUP_MSG:
            # Emit an expected log message so launcher.py knows we've started up.
            print(STARTUP_MSG)
            # We've seen some issues with stdout buffering - be conservative.
            sys.stdout.flush()

        logger.info(f"Schedule auto shutdown with timout {self.timeout}")
        self.shutdown_schedule()

        logger.info("awaiting running future")
        await self.completion

    async def stop(self):
        # Clear all sessions first
        print("Clearing all sessions before shutdown...")
        logger.info("Clearing all sessions before shutdown...")
        self.auth_manager.clear_all_sessions()

        # For debugging, check the sessions in the application state
        print("Before clearing application state sessions")
        logger.info("Before clearing application state sessions")
        print("self.app['state']['sessions']:", self.app['state']['sessions'])
        logger.info(f"App state sessions: {self.app['state']['sessions']}")
        
        # Clear the application state sessions 
        self.app['state']['sessions'].clear()
        print("Cleared application state sessions")
        logger.info("Cleared application state sessions")

        # For debugging, check the sessions in the application state after clearing
        print("After clearing application state sessions")
        logger.info("After clearing application state sessions")
        print("self.app['state']['sessions']:", self.app['state']['sessions'])
        logger.info(f"App state sessions: {self.app['state']['sessions']}")

        # Disconnecting any connected clients of handler(s)
        print("Disconnecting all clients...")
        logger.info("Disconnecting all clients...")
        for handler in self._ws_handlers:
            await handler.disconnectClients()

        # Neither site.stop() nor runner.cleanup() actually stop the server
        # as documented, but at least runner.cleanup() results in the
        # "on_shutdown" signal getting sent.
        print("Performing runner.cleanup()")
        logger.info("Performing runner.cleanup()")
        await self.runner.cleanup()

        # So to actually stop the server, the workaround is just to resolve
        # the future we awaited in the start method.
        print("Stopping server")
        logger.info("Stopping server")
        self.completion.set_result(True)
        print("Server shutdown complete")
        logger.info("Server shutdown complete")

# -----------------------------------------------------------------------------
# Class that handles reverse connection (server initiates connection to client)
# -----------------------------------------------------------------------------

class ReverseWebAppServer(AbstractWebApp):
    def __init__(self, server_config):
        super().__init__(server_config)
        self._url = server_config.get("reverse_url")
        self._server_protocol = server_config.get("ws_protocol")
        self._ws_handler = AioHttpWsHandler(self._server_protocol, self)

    async def start(self, port_callback=None):
        if port_callback is not None:
            port_callback(0)

        await self._ws_handler.reverse_connect_to(self._url)

    async def stop(self):
        client_id = self._ws_handler.reverse_connection_client_id
        ws = self._ws_handler.connections[client_id]
        await ws.close()

# -----------------------------------------------------------------------------
# Function to create a web server, this is the main entry point for the backend
# -----------------------------------------------------------------------------

def create_webserver(server_config):
    if "logging_level" in server_config and server_config["logging_level"]:
        logging.getLogger("wslink").setLevel(server_config["logging_level"])

    # Shortcut for reverse connection
    if "reverse_url" in server_config:
        return ReverseWebAppServer(server_config)

    # Normal web server
    # print("Creating WebAppServer with config:", server_config)
    return WebAppServer(server_config)

# -----------------------------------------------------------------------------
# Function which checks if the message type is binary, useful for handling data
# -----------------------------------------------------------------------------

def is_binary(msg):
    return msg.type == aiohttp.WSMsgType.BINARY

# -----------------------------------------------------------------------------
# Class that extends WslinkHandler to handle WebSocket connections with aiohttp
# -----------------------------------------------------------------------------

class AioHttpWsHandler(WslinkHandler):
    async def disconnectClients(self):
        print("\n=== Starting Client Disconnection Process ===")
        print("Closing client connections...")
        # Create a copy of keys to avoid modification during iteration
        keys = list(self.connections.keys())
        print(f"Found {len(keys)} active connections to close")
        
        for client_id in keys:
            try:
                print(f"\n--- Processing client {client_id} ---")
                if client_id not in self.connections:
                    print(f"Client {client_id} already disconnected, skipping...")
                    continue
                    
                ws = self.connections[client_id]
                request = ws._req

                if request:
                    print("\nChecking cookies:")
                    print(f"Current cookies: {request.cookies}")
                    
                    session_id = request.cookies.get('auth_session')
                    if session_id:
                        # Invalidate session and clean up
                        print(f"\nFound session {session_id} to invalidate")
                        
                        if hasattr(self.web_app, 'auth_manager'):
                            print("\n-> Adding to blacklist and cleaning up sessions")
                            self.auth_manager = self.web_app.auth_manager
                            
                            print("Before blacklisting:")
                            print(f"Blacklist size: {len(self.auth_manager._blacklisted_tokens)}")
                            print(f"Current blacklist: {self.auth_manager._blacklisted_tokens}")
                            
                            self.auth_manager._blacklisted_tokens.add(session_id)
                            
                            print("\nAfter blacklisting:")
                            print(f"Blacklist size: {len(self.auth_manager._blacklisted_tokens)}")
                            print(f"Updated blacklist: {self.auth_manager._blacklisted_tokens}")
                            
                            if session_id in self.auth_manager._sessions:
                                print("\n-> Removing from active sessions")
                                print(f"Before removal - Active sessions: {self.auth_manager._sessions}")
                                del self.auth_manager._sessions[session_id]
                                print(f"After removal - Active sessions: {self.auth_manager._sessions}")

                        print("\n-> Setting up cookie invalidation")
                        response = aiohttp.web.Response()
                        
                        # Two methods to invalidate the cookie
                        print("Attempting Method 1: Set immediate expiration")
                        response.set_cookie(
                            'auth_session',
                            '',
                            expires=datetime.now() - timedelta(days=1),
                            max_age=0,
                            path='/',
                            domain=None,
                            secure=True,
                            httponly=True,
                            samesite='Strict'
                        )
                        print(f"Cookie headers after Method 1: {response.headers.get('Set-Cookie', 'No cookie header')}")
                        
                        print("\nAttempting Method 2: Override with expired version")
                        response.headers['Set-Cookie'] = (
                            'auth_session=deleted; '
                            'Path=/; '
                            'Expires=Thu, 01 Jan 1970 00:00:00 GMT; '
                            'Max-Age=0; '
                            'Secure; '
                            'HttpOnly; '
                            'SameSite=Strict'
                        )
                        print(f"Final cookie headers: {response.headers.get('Set-Cookie', 'No cookie header')}")

                        if 'state' in self.web_app.app and 'sessions' in self.web_app.app['state']:
                            print("\n-> Clearing application state")
                            print(f"Before clearing - App sessions: {self.web_app.app['state']['sessions']}")
                            self.web_app.app['state']['sessions'].discard(session_id)
                            print(f"After clearing - App sessions: {self.web_app.app['state']['sessions']}")

                        # Send invalidation message while connection is still active
                        print("\n-> Sending invalidation message to client")
                        try:
                            invalidation_message = json.dumps({
                                'type': 'session_invalidated',
                                'message': 'Session has been invalidated'
                            })
                            print(f"Sending message: {invalidation_message}")
                            await ws.send_str(invalidation_message)
                            print("Invalidation message sent successfully")
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            print(f"ERROR sending invalidation message: {str(e)}")

                        print("\n-> Closing WebSocket connection")
                        try:
                            if client_id in self.connections:
                                await ws.close(
                                    code=aiohttp.WSCloseCode.GOING_AWAY,
                                    message=b"Session invalidated and connection closed"
                                )
                                print(f"Successfully closed WebSocket for client {client_id}")
                                await asyncio.sleep(0.1)
                                
                                # Only remove if still present after close
                                if client_id in self.connections:
                                    print(f"\n-> Removing client {client_id} from connections dictionary")
                                    del self.connections[client_id]
                                    print("Connection removed successfully")
                        except Exception as e:
                            print(f"ERROR closing WebSocket: {str(e)}")

            except Exception as e:
                print(f"Error processing client {client_id}: {str(e)}")
                # Ensure connection is removed even if there's an error
                if client_id in self.connections:
                    del self.connections[client_id]

        print("\n-> Unregistering protocol")
        try:
            self.publishManager.unregisterProtocol(self)
        except Exception as e:
            print(f"Error unregistering protocol: {str(e)}")

        print("\n=== Performing Final Cleanup ===")
        remaining_connections = len(self.connections)
        if remaining_connections > 0:
            print(f"Warning: {remaining_connections} connections still present")
            print("Remaining connections:", list(self.connections.keys()))
            self.connections.clear()
        else:
            print("All connections successfully cleared")
        
        if hasattr(self, 'auth_manager'):
            print("\nFinal Session State:")
            print(f"Active sessions: {self.auth_manager._sessions}")
            print(f"Blacklisted tokens: {self.auth_manager._blacklisted_tokens}")
            print(f"Total blacklisted tokens: {len(self.auth_manager._blacklisted_tokens)}")
        
        print("\n=== Disconnection Process Complete ===\n")

    async def handleWsRequest(self, request):
        client_id = str(uuid.uuid4()).replace("-", "")
        current_ws = aiohttp_web.WebSocketResponse(
            max_msg_size=MSG_OVERHEAD + MAX_MSG_SIZE, heartbeat=HEART_BEAT
        )
        self.connections[client_id] = current_ws

        logger.info("client {0} connected".format(client_id))
        print("client {0} connected".format(client_id))

        self.web_app.shutdown_cancel()

        try:
            await current_ws.prepare(request)
            await self.onConnect(request, client_id)
            async for msg in current_ws:
                if client_id in self.connections:  # Check if client still connected
                    await self.onMessage(is_binary(msg), msg, client_id)
        except Exception as e:
            logger.error(f"Error in handleWsRequest for client {client_id}: {str(e)}")
            print(f"Error in handleWsRequest for client {client_id}: {str(e)}")
        finally:
            try:
                if client_id in self.connections:
                    await self.onClose(client_id)
                    del self.connections[client_id]
                    self.authentified_client_ids.discard(client_id)
                    logger.info("client {0} disconnected".format(client_id))
                    print("client {0} disconnected".format(client_id))

                    if not self.connections:
                        logger.info("No more connections, scheduling shutdown")
                        print("No more connections, scheduling shutdown")
                        self.web_app.shutdown_schedule()
            except Exception as e:
                logger.error(f"Error in cleanup for client {client_id}: {str(e)}")
                print(f"Error in cleanup for client {client_id}: {str(e)}")

        return current_ws

    async def reverse_connect_to(self, url):
        logger.debug("reverse_connect_to: running with url %s", url)
        print("reverse_connect_to: running with url", url)
        client_id = self.reverse_connection_client_id
        async with aiohttp.ClientSession() as session:
            logger.debug("reverse_connect_to: client session started")
            print("reverse_connect_to: client session started")
            async with session.ws_connect(url) as current_ws:
                logger.debug("reverse_connect_to: ws started")
                print("reverse_connect_to: ws started")
                self.connections[client_id] = current_ws
                logger.debug("reverse_connect_to: onConnect")
                print("reverse_connect_to: onConnect")
                await self.onConnect(url, client_id)

                async for msg in current_ws:
                    if not current_ws.closed:
                        await self.onMessage(is_binary(msg), msg, client_id)

                logger.debug("reverse_connect_to: onClose")
                print("reverse_connect_to: onClose")
                await self.onClose(client_id)
                del self.connections[client_id]

        logger.debug("reverse_connect_to: exited")
        print("reverse_connect_to: exited")