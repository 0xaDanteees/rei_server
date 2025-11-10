from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, partner_id: str):
        """Connect a WebSocket for a specific partner"""
        await websocket.accept()
        if partner_id not in self.active_connections:
            self.active_connections[partner_id] = []
        self.active_connections[partner_id].append(websocket)
        logger.info(f"WebSocket connected for partner {partner_id}")

    def disconnect(self, websocket: WebSocket, partner_id: str):
        """Disconnect a WebSocket for a specific partner"""
        if partner_id in self.active_connections:
            try:
                self.active_connections[partner_id].remove(websocket)
                if not self.active_connections[partner_id]:
                    del self.active_connections[partner_id]
                logger.info(f"WebSocket disconnected for partner {partner_id}")
            except ValueError:
                pass  # WebSocket was already removed

    async def send_reaction(self, partner_id: str, emotion: str, intensity: float = 1.0, message: str = None):
        """Send emotion reaction to all connected clients for a partner"""
        if partner_id not in self.active_connections:
            logger.warning(f"No active connections for partner {partner_id}")
            return

        reaction_message = {
            "type": "emotion",
            "data": {
                "emotion": emotion,
                "intensity": intensity,
                "partnerId": partner_id,
                "message": message,
                "timestamp": json.dumps({"$date": {"$numberLong": str(int(__import__('time').time() * 1000))}})
            }
        }

        disconnected_connections = []
        for connection in self.active_connections[partner_id]:
            try:
                await connection.send_text(json.dumps(reaction_message))
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket: {e}")
                disconnected_connections.append(connection)

        # Clean up disconnected connections
        for connection in disconnected_connections:
            self.disconnect(connection, partner_id)

    async def send_rag_response(self, partner_id: str, response: str, emotion: str = None, intensity: float = 1.0):
        """Send RAG response with optional emotion to connected clients"""
        if partner_id not in self.active_connections:
            logger.warning(f"No active connections for partner {partner_id}")
            return

        rag_message = {
            "type": "rag_response",
            "data": {
                "response": response,
                "emotion": emotion,
                "intensity": intensity,
                "partnerId": partner_id,
                "timestamp": json.dumps({"$date": {"$numberLong": str(int(__import__('time').time() * 1000))}})
            }
        }

        disconnected_connections = []
        for connection in self.active_connections[partner_id]:
            try:
                await connection.send_text(json.dumps(rag_message))
            except Exception as e:
                logger.error(f"Failed to send RAG response to WebSocket: {e}")
                disconnected_connections.append(connection)

        # Clean up disconnected connections
        for connection in disconnected_connections:
            self.disconnect(connection, partner_id)

    async def broadcast_to_partner(self, partner_id: str, message_type: str, data: dict):
        """Broadcast a custom message to all connections for a partner"""
        if partner_id not in self.active_connections:
            return

        message = {
            "type": message_type,
            "data": {
                **data,
                "partnerId": partner_id,
                "timestamp": json.dumps({"$date": {"$numberLong": str(int(__import__('time').time() * 1000))}})
            }
        }

        disconnected_connections = []
        for connection in self.active_connections[partner_id]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to broadcast message to WebSocket: {e}")
                disconnected_connections.append(connection)

        # Clean up disconnected connections
        for connection in disconnected_connections:
            self.disconnect(connection, partner_id)

    def get_connection_count(self, partner_id: str = None) -> int:
        """Get the number of active connections for a partner or total"""
        if partner_id:
            return len(self.active_connections.get(partner_id, []))
        return sum(len(connections) for connections in self.active_connections.values())

# Global connection manager instance
manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, partner_id: str):
    """WebSocket endpoint for avatar reactions"""
    await manager.connect(websocket, partner_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                # Handle different message types from client
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message.get("type") == "trigger_reaction":
                    # Allow client to trigger reactions for testing
                    emotion = message.get("data", {}).get("emotion", "happy")
                    intensity = message.get("data", {}).get("intensity", 1.0)
                    await manager.send_reaction(partner_id, emotion, intensity)
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from WebSocket: {data}")
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, partner_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, partner_id)
