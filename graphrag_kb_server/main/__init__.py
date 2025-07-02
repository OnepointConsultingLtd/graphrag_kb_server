import socketio

from graphrag_kb_server.config import websocket_cfg

from .project_server import routes as server_routes
from .multi_tennant_server import routes as tennant_routes
from .pdf_server import routes as pdf_routes
from .search_server import routes as search_routes
from .linkedin_server import routes as linkedin_routes

sio = socketio.AsyncServer(
    async_mode="aiohttp",
    cors_allowed_origins=websocket_cfg.websocket_cors_allowed_origins,
)

all_routes = [tennant_routes, server_routes, pdf_routes, search_routes, linkedin_routes]
