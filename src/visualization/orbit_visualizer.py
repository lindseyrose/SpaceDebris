"""3D visualization of space debris using Three.js."""
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import asyncio
from pathlib import Path
from typing import Dict, List
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.sample_data import DebrisGenerator
from src.data.debris_aggregator import DebrisAggregator
from src.data.space_track_client import SpaceTrackClient
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

class OrbitVisualizer:
    def __init__(self):
        self.generator = DebrisGenerator()
        self.aggregator = DebrisAggregator()
        self.space_track = SpaceTrackClient()
        self.all_objects = []
        self.update_interval = 30 * 60  # 30 minutes in seconds
        self.connected_clients: List[WebSocket] = []
        self.start_time = datetime.now()
        
    async def initialize(self):
        await self.initialize_objects()
        # Start periodic updates
        asyncio.create_task(self._periodic_updates())
        return self
    
    async def fetch_space_data(self):
        """Fetch aggregated space objects data from all sources."""
        try:
            # Fetch both debris and satellites
            debris_data = await self.aggregator.get_aggregated_data(days_ago=1, use_cache=True)
            satellite_data = await self.space_track.fetch_space_objects(object_type='PAYLOAD', days_ago=1, use_cache=True)
            
            total_objects = len(debris_data) + len(satellite_data)
            logging.info(f"Got {len(debris_data)} debris objects and {len(satellite_data)} satellites")
            
            return debris_data + satellite_data
        except Exception as e:
            logging.error(f"Error fetching space data: {str(e)}")
            return []

    async def initialize_objects(self):
        """Initialize objects with real data."""
        logging.info("Initializing objects...")
        
        # Start with sample data until we get real data
        satellites = self.generator.generate_satellites(10)
        debris = self.generator.generate_debris(50)
        
        self.all_objects = debris + satellites
        logging.info(f"Generated initial objects: {len(debris)} debris and {len(satellites)} satellites")
        
        # Get real data immediately
        await self.update_with_real_data()

    async def update_with_real_data(self):
        """Update space objects with real data from all sources."""
        try:
            real_objects = await self.fetch_space_data()
            if real_objects:
                # Replace all objects with real data
                self.all_objects = real_objects
                
                # Count objects by type
                debris_count = sum(1 for obj in real_objects if obj['type'] == 'debris')
                satellite_count = sum(1 for obj in real_objects if obj['type'] == 'satellite')
                
                logging.info(f"Updated to {debris_count} debris and {satellite_count} satellites")
                
                # Notify all connected clients about the update
                update_message = {
                    'type': 'update',
                    'message': f'Updated space objects: {debris_count} debris and {satellite_count} satellites'
                }
                await self.broadcast_message(update_message)
        except Exception as e:
            logging.error(f"Failed to update with real data: {str(e)}")
    
    async def _periodic_updates(self):
        """Periodically update debris data."""
        while True:
            try:
                await asyncio.sleep(self.update_interval)
                logging.info("Running periodic update of debris data...")
                await self.update_with_real_data()
            except Exception as e:
                logging.error(f"Error in periodic update: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def register_client(self, websocket: WebSocket):
        """Register a new WebSocket client."""
        try:
            logger.debug("New WebSocket client connecting from %s", websocket.client)
            await websocket.accept()
            logger.info("WebSocket connection accepted from %s", websocket.client)
            
            self.connected_clients.append(websocket)
            logger.info(f"Client registered. Total clients: {len(self.connected_clients)}")
            
            # Send initial object data
            updated_objects = self.all_objects
            logging.info(f"Sending {len(updated_objects)} objects to new client")
            
            # Log a sample of objects
            for i, obj in enumerate(updated_objects[:5]):
                logging.info(f"Sample object {i + 1}: {obj}")
            
            # Send objects in batches to avoid overwhelming the connection
            batch_size = 10
            sent_count = 0
            
            for i in range(0, len(updated_objects), batch_size):
                batch = updated_objects[i:i + batch_size]
                try:
                    # Send batch as a single message
                    batch_data = {
                        'type': 'batch_update',
                        'objects': batch
                    }
                    await websocket.send_json(batch_data)
                    sent_count += len(batch)
                    
                    logging.info(f"Sent batch {i//batch_size + 1}, total objects sent: {sent_count}/{len(updated_objects)}")
                    
                    # Small delay between batches to prevent overwhelming the client
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logging.error(f"Failed to send batch starting at index {i}: {str(e)}")
                    break
            
            logging.info(f"Successfully sent {sent_count} objects to client")
            
        except Exception as e:
            logging.error(f"Error in register_client: {str(e)}")
            if websocket in self.connected_clients:
                self.connected_clients.remove(websocket)

    async def broadcast_message(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected_clients = []
        
        for client in self.connected_clients:
            try:
                await client.send_json(message)
            except Exception as e:
                logging.error(f"Error sending message to client: {str(e)}")
                disconnected_clients.append(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            try:
                self.connected_clients.remove(client)
            except ValueError:
                pass

    def update_debris_data(self, debris_id: str, position: dict):
        """Update position data for a specific debris object."""
        self.debris_data[debris_id] = position
        asyncio.create_task(self._broadcast_update(debris_id))
    
    async def _broadcast_update(self, debris_id: str):
        """Broadcast position updates to all connected clients."""
        if not self.connected_clients:
            return
            
        update_data = {
            "id": debris_id,
            "position": self.debris_data[debris_id]
        }
        
        for client in self.connected_clients:
            try:
                await client.send_text(json.dumps(update_data))
            except Exception as e:
                logging.error(f"Error sending update to client: {str(e)}")
                self.connected_clients.remove(client)

async def create_visualizer():
    visualizer = OrbitVisualizer()
    await visualizer.initialize()
    return visualizer

visualizer = None

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global visualizer
    if visualizer is None:
        visualizer = await create_visualizer()
    
    await visualizer.register_client(websocket)
    try:
        while True:
            # Update and send positions every second
            await asyncio.sleep(1)
            time_offset = (datetime.now() - visualizer.start_time).total_seconds()
            updated_objects = visualizer.generator.update_positions(
                visualizer.all_objects,
                time_offset
            )
            logging.info(f"Updating {len(updated_objects)} objects")
            for obj in updated_objects:
                try:
                    # Log a sample of objects (every 10th one to avoid too much logging)
                    if int(obj['id']) % 10 == 0:
                        logging.info(f"Sending update for object {obj['id']} at position {obj['position']}")
                    await websocket.send_text(json.dumps(obj))
                except Exception as e:
                    logging.error(f"Error sending update for object {obj['id']}: {str(e)}")
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
        if websocket in visualizer.connected_clients:
            visualizer.connected_clients.remove(websocket)

# Serve static files (HTML, JS, CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.get("/favicon.ico")
async def get_favicon():
    return FileResponse("static/favicon.ico", media_type="image/x-icon")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8080)
