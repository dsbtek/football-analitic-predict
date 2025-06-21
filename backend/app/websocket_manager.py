"""
WebSocket manager for real-time updates in the Football Analytics Predictor.
"""

import json
import asyncio
import logging
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db import SessionLocal, Match
from app.security import verify_token

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Store active connections by user ID
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store anonymous connections
        self.anonymous_connections: Set[WebSocket] = set()
        # Store user sessions
        self.user_sessions: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        if user_id:
            # Authenticated user
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
            self.user_sessions[websocket] = user_id
            logger.info(f"User {user_id} connected via WebSocket")
        else:
            # Anonymous user
            self.anonymous_connections.add(websocket)
            logger.info("Anonymous user connected via WebSocket")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        # Remove from user connections
        if websocket in self.user_sessions:
            user_id = self.user_sessions[websocket]
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            del self.user_sessions[websocket]
            logger.info(f"User {user_id} disconnected from WebSocket")
        
        # Remove from anonymous connections
        self.anonymous_connections.discard(websocket)
        logger.info("WebSocket connection closed")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.add(websocket)
            
            # Clean up disconnected websockets
            for websocket in disconnected:
                self.active_connections[user_id].discard(websocket)
    
    async def broadcast(self, message: dict, include_anonymous: bool = True):
        """Broadcast a message to all connected clients."""
        message_str = json.dumps(message)
        disconnected = set()
        
        # Send to authenticated users
        for user_id, connections in self.active_connections.items():
            for websocket in connections.copy():
                try:
                    await websocket.send_text(message_str)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    disconnected.add(websocket)
        
        # Send to anonymous users
        if include_anonymous:
            for websocket in self.anonymous_connections.copy():
                try:
                    await websocket.send_text(message_str)
                except Exception as e:
                    logger.error(f"Error broadcasting to anonymous user: {e}")
                    disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total_authenticated = sum(len(connections) for connections in self.active_connections.values())
        total_anonymous = len(self.anonymous_connections)
        
        return {
            "total_connections": total_authenticated + total_anonymous,
            "authenticated_users": len(self.active_connections),
            "authenticated_connections": total_authenticated,
            "anonymous_connections": total_anonymous,
            "timestamp": datetime.utcnow().isoformat()
        }


class RealTimeUpdater:
    """Handles real-time data updates and notifications."""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.last_update = datetime.utcnow()
        self.update_interval = 30  # seconds
    
    async def start_background_updates(self):
        """Start background task for periodic updates."""
        while True:
            try:
                await self.check_and_send_updates()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in background updates: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def check_and_send_updates(self):
        """Check for data updates and send to clients."""
        try:
            # Get latest matches from database
            session = SessionLocal()
            try:
                matches = session.query(Match).all()
                
                if matches:
                    # Convert to JSON-serializable format
                    matches_data = []
                    for match in matches:
                        match_dict = {
                            "id": match.id,
                            "home": match.home,
                            "away": match.away,
                            "bookmaker": match.bookmaker,
                            "home_odds": match.home_odds,
                            "draw_odds": match.draw_odds,
                            "away_odds": match.away_odds,
                            "value_home": round(match.value_home, 2) if match.value_home else 0,
                            "value_draw": round(match.value_draw, 2) if match.value_draw else 0,
                            "value_away": round(match.value_away, 2) if match.value_away else 0,
                            "start_time": match.start_time.isoformat() if match.start_time else None,
                            "best_value": max(
                                match.value_home or 0,
                                match.value_draw or 0,
                                match.value_away or 0
                            )
                        }
                        matches_data.append(match_dict)
                    
                    # Sort by best value
                    matches_data.sort(key=lambda x: x["best_value"], reverse=True)
                    
                    # Send update to all clients
                    update_message = {
                        "type": "matches_update",
                        "data": matches_data[:20],  # Send top 20 matches
                        "timestamp": datetime.utcnow().isoformat(),
                        "total_matches": len(matches_data)
                    }
                    
                    await self.connection_manager.broadcast(update_message)
                    self.last_update = datetime.utcnow()
                    
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
    
    async def send_odds_refresh_notification(self):
        """Send notification when odds are being refreshed."""
        message = {
            "type": "odds_refresh_started",
            "message": "Odds refresh in progress...",
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.connection_manager.broadcast(message)
    
    async def send_odds_refresh_complete(self, new_matches_count: int):
        """Send notification when odds refresh is complete."""
        message = {
            "type": "odds_refresh_complete",
            "message": f"Odds refresh complete! {new_matches_count} value bets found.",
            "new_matches_count": new_matches_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.connection_manager.broadcast(message)
    
    async def send_cart_update(self, user_id: str, cart_data: dict):
        """Send cart update to specific user."""
        message = {
            "type": "cart_update",
            "data": cart_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.connection_manager.send_personal_message(message, user_id)
    
    async def send_system_notification(self, notification_type: str, message: str, level: str = "info"):
        """Send system notification to all users."""
        notification = {
            "type": "system_notification",
            "notification_type": notification_type,
            "message": message,
            "level": level,  # info, warning, error
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.connection_manager.broadcast(notification)


# Global instances
connection_manager = ConnectionManager()
real_time_updater = RealTimeUpdater(connection_manager)


async def authenticate_websocket(websocket: WebSocket, token: Optional[str] = None) -> Optional[str]:
    """Authenticate WebSocket connection using JWT token."""
    if not token:
        return None
    
    try:
        payload = verify_token(token)
        user_id = payload.get("user_id")
        return str(user_id) if user_id else None
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        return None


async def handle_websocket_message(websocket: WebSocket, message: dict, user_id: Optional[str] = None):
    """Handle incoming WebSocket messages."""
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping with pong
        await websocket.send_text(json.dumps({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    elif message_type == "subscribe_matches":
        # Send current matches immediately
        await real_time_updater.check_and_send_updates()
    
    elif message_type == "get_stats":
        # Send connection statistics
        stats = connection_manager.get_connection_stats()
        await websocket.send_text(json.dumps({
            "type": "connection_stats",
            "data": stats
        }))
    
    else:
        logger.warning(f"Unknown WebSocket message type: {message_type}")


# Background task starter
async def start_real_time_updates():
    """Start the real-time update background task."""
    asyncio.create_task(real_time_updater.start_background_updates())
