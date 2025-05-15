"""
WebSocket server for space debris visualization.
"""

import asyncio
import json
import logging
import websockets
from data.mock_data import generate_mock_debris

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DebrisServer:
    def __init__(self):
        self.clients = set()
        
    async def send_debris_data(self):
        """Periodically fetch and send debris data to all connected clients."""
        first_update = True
        while True:
            try:
                logger.info('Generating mock debris data...')
                # Generate mock data
                viz_data = generate_mock_debris(count=50)
                
                # Send to all connected clients
                if self.clients:
                    message = json.dumps(viz_data)
                    logger.info(f'Sending data to {len(self.clients)} clients: {message[:200]}...')
                    await asyncio.gather(
                        *[client.send(message) for client in self.clients]
                    )
                    logger.info(f'Successfully sent data to {len(self.clients)} clients')
                
            except Exception as e:
                logger.error(f"Error sending debris data: {e}")
            
            # Wait before sending next update
            if first_update:
                await asyncio.sleep(1)  # Send next update quickly for initial data
                first_update = False
            else:
                await asyncio.sleep(300)  # Then update every 5 minutes
    
    async def handle_client(self, websocket):
        """Handle a client connection."""
        try:
            # Send initial data immediately
            viz_data = generate_mock_debris(count=50)
            message = json.dumps(viz_data)
            await websocket.send(message)
            logger.info("Sent initial data to new client")
            
            # Add to client set
            self.clients.add(websocket)
            logger.info("Client connected")
            
            # Keep the connection alive
            await websocket.wait_closed()
            
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            self.clients.remove(websocket)

async def main():
    server = DebrisServer()
    
    # Start the data sending task
    asyncio.create_task(server.send_debris_data())
    
    # Start the WebSocket server
    async with websockets.serve(lambda ws: server.handle_client(ws), "localhost", 8765):
        logger.info("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
