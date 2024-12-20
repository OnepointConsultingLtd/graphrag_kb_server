from .server import routes as server_routes
from .multi_tennant_server import routes as tennant_routes
from .multi_tennant_server import auth_middleware

all_routes = [tennant_routes, server_routes]
