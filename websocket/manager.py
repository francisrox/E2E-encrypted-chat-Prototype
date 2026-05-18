from fastapi import WebSocket
from typing import Dict
import json


class ConnectionManager:
    def __init__(self):
        # Maps user_uuid -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_uuid: str):
        await websocket.accept()
        self.active_connections[user_uuid] = websocket

    def disconnect(self, user_uuid: str):
        self.active_connections.pop(user_uuid, None)

    async def send_to_user(self, user_uuid: str, data: dict):
        ws = self.active_connections.get(user_uuid)
        if ws:
            await ws.send_text(json.dumps(data))

    def is_online(self, user_uuid: str) -> bool:
        return user_uuid in self.active_connections


manager = ConnectionManager()
