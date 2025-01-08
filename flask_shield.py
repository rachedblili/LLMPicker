import ipaddress
from flask import request, jsonify


class FlaskShield:
    def __init__(self, app=None, authorized_tokens=None, allowed_ips=None, trust_proxy=False, require_token=True):
        """
        Initialize the FlaskShield

        :param app: Flask application instance (optional)
        :param authorized_tokens: List of valid bearer tokens
        :param allowed_ips: List of allowed IP networks
        :param trust_proxy: Boolean indicating whether to trust proxy headers
                            and use the client IP from X-Forwarded-For.
                            If False, only the direct connection IP is checked.
        :param require_token: Boolean indicating whether token authentication is required.
                            If False, only IP-based authentication will be performed.
        """
        self._authorized_tokens = set(authorized_tokens or [])
        self._allowed_ips = set(allowed_ips or [])
        self._exempt_routes = set()
        self._trust_proxy = trust_proxy
        self._require_token = require_token

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialize the middleware with a Flask app

        :param app: Flask application instance
        """
        app.before_request(self._check_auth)

        # Store middleware instance on the app for access
        app.extensions = app.extensions or {}
        app.extensions['flask_shield'] = self

    def _is_ip_allowed(self, ip_address):
        """
        Check if the given IP address is in the allowed list

        :param ip_address: IP address to check
        :return: Boolean indicating if IP is allowed
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            return any(
                ip in ipaddress.ip_network(allowed_ip, strict=False)
                for allowed_ip in self._allowed_ips
            )
        except ValueError:
            return False

    def _get_client_ip(self):
        """
        Retrieve the client IP address, considering common proxy headers

        :return: Client IP address
        """
        if self._trust_proxy:
            return request.remote_addr

        headers_to_check = [
            'X-Forwarded-For',
            'X-Real-IP',
            'Remote-Addr'
        ]

        for header in headers_to_check:
            ip = request.headers.get(header) or request.remote_addr
            if ip:
                # If X-Forwarded-For might contain multiple IPs, take the first
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                return ip

        return request.remote_addr

    def _check_auth(self):
        """
        Authentication check to be used with before_request
        """
        # Skip authentication for exempt routes
        if request.endpoint in self._exempt_routes:
            return None

        # Check IP
        client_ip = self._get_client_ip()
        if not self._is_ip_allowed(client_ip):
            return jsonify({
                "error": "Unauthorized",
                "message": f"IP {client_ip} is not allowed"
            }), 403

        # If token authentication is not required, return after IP check
        if not self._require_token:
            return None

        # Check Bearer Token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                "error": "Unauthorized",
                "message": "Missing Authorization header"
            }), 401

        # Extract and validate token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                "error": "Unauthorized",
                "message": "Invalid Authorization header format"
            }), 401

        token = parts[1]
        if token not in self._authorized_tokens:
            return jsonify({
                "error": "Unauthorized",
                "message": "Invalid token"
            }), 401

        # If all checks pass, continue with the request
        return None

    def exempt_route(self, route_name):
        """
        Exempt a specific route from authentication

        :param route_name: Name of the route to exempt
        """
        self._exempt_routes.add(route_name)

    def add_token(self, token):
        """
        Add a new authorized token

        :param token: Token to add
        """
        self._authorized_tokens.add(token)

    def add_allowed_ip(self, ip):
        """
        Add a new allowed IP or IP network

        :param ip: IP or CIDR network to add
        """
        self._allowed_ips.add(ip)
