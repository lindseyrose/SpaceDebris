from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import logging
import random

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

class RateLimiter:
    def __init__(self, requests_per_window: int = 1, window_seconds: int = 30):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.requests = []

    async def acquire(self) -> bool:
        now = datetime.now()
        # Remove old requests
        self.requests = [ts for ts in self.requests if (now - ts).total_seconds() < self.window_seconds]
        
        if len(self.requests) < self.requests_per_window:
            self.requests.append(now)
            return True
        return False

    async def wait_for_slot(self) -> None:
        while not await self.acquire():
            await asyncio.sleep(1)

# Create FastAPI app, rate limiter, and cache
app = FastAPI()
rate_limiter = RateLimiter(requests_per_window=1, window_seconds=60)  # Increase window to 60 seconds

# Cache for space objects data
class DataCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes TTL
        self.data = None
        self.last_update = None
        self.ttl_seconds = ttl_seconds

    def set(self, data: list) -> None:
        self.data = data
        self.last_update = datetime.now()

    def get(self) -> list:
        if not self.data or not self.last_update:
            return None
        if (datetime.now() - self.last_update).total_seconds() > self.ttl_seconds:
            return None
        return self.data

space_objects_cache = DataCache()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store Space-Track.org credentials
SPACE_TRACK_USER = os.getenv('SPACETRACK_EMAIL')
SPACE_TRACK_PASS = os.getenv('SPACETRACK_PASSWORD')
SPACE_TRACK_URL = "https://www.space-track.org"

async def get_space_track_session():
    """Get authenticated session for Space-Track.org"""
    if not SPACE_TRACK_USER or not SPACE_TRACK_PASS:
        logging.error("Space-Track.org credentials not found in environment variables")
        return None
        
    auth_data = {
        'identity': SPACE_TRACK_USER,
        'password': SPACE_TRACK_PASS
    }
    
    try:
        client = httpx.AsyncClient()
        
        # First try to get the login page to get any required cookies
        login_response = await client.get(f"{SPACE_TRACK_URL}/auth/login")
        logging.info(f"Login page response: {login_response.status_code}")
        logging.info(f"Login page cookies: {dict(login_response.cookies)}")
        
        # Now attempt to login
        response = await client.post(
            f"{SPACE_TRACK_URL}/ajaxauth/login",
            data=auth_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        
        logging.info(f"Login response: {response.status_code}")
        logging.info(f"Login response headers: {dict(response.headers)}")
        logging.info(f"Login response cookies: {dict(response.cookies)}")
        
        if response.status_code == 200:
            logging.info("Successfully authenticated with Space-Track.org")
            return client
        else:
            logging.error(f"Space-Track.org authentication failed: {response.status_code} - {response.text}")
            await client.aclose()
            return None
    except Exception as e:
        logging.error(f"Error during Space-Track.org authentication: {str(e)}")
        if 'client' in locals():
            await client.aclose()
        return None

async def fetch_space_objects():
    """Fetch recent space objects data from Space-Track.org"""
    client = await get_space_track_session()
    if not client:
        logging.error("Failed to get Space-Track.org session")
        return []
    
    try:
        # Get data from last 30 days
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        current_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Query for active debris and payloads with recent data
        query_url = f"{SPACE_TRACK_URL}/basicspacedata/query/class/gp/OBJECT_TYPE/DEBRIS,PAYLOAD/EPOCH/{thirty_days_ago}--{current_date}/DECAY_DATE/null-val/orderby/EPOCH desc/limit/50/format/json"  # Reduce limit to 50
        
        logging.info(f"Fetching data from: {query_url}")
        
        max_retries = 3  # Reduce max retries
        retry_delay = 60  # Increase initial delay to 60 seconds
        
        for attempt in range(max_retries):
            # Wait for rate limiter
            await rate_limiter.wait_for_slot()
            
            response = await client.get(
                query_url,
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
            )
            
            logging.info(f"Data response: {response.status_code}")
            logging.info(f"Data response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check for error response
                    if isinstance(data, dict) and 'error' in data:
                        error_msg = data['error'].lower()
                        if 'rate limit' in error_msg:
                            if attempt < max_retries - 1:
                                # Calculate exponential backoff with jitter
                                backoff = min(300, retry_delay * (2 ** attempt))  # Cap at 5 minutes
                                jitter = random.uniform(0, 0.1 * backoff)  # Add 0-10% jitter
                                wait_time = backoff + jitter
                                
                                logging.warning(f"Rate limit hit, waiting {wait_time:.1f} seconds before retry {attempt + 1}/{max_retries}")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                logging.error("Rate limit persists after all retries")
                                return []
                        else:
                            logging.error(f"API error: {data['error']}")
                            return []
                    
                    # Check for valid data format
                    if isinstance(data, list):
                        if not data:  # Empty list
                            logging.warning("No space objects data returned")
                            return []
                        
                        logging.info(f"Successfully fetched {len(data)} objects from Space-Track.org")
                        logging.info(f"Sample data: {data[0] if data else 'No data'}")
                        processed_data = process_space_objects(data)
                        if processed_data:
                            return processed_data
                        else:
                            if attempt < max_retries - 1:
                                logging.warning("Failed to process data, retrying...")
                                await asyncio.sleep(retry_delay)
                                continue
                            return []
                    else:
                        logging.error(f"Unexpected data format: {data}")
                        return []
                        
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse JSON response: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return []
            else:
                if attempt < max_retries - 1:
                    logging.warning(f"Request failed with status {response.status_code}, retrying in {retry_delay} seconds")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logging.error(f"Failed to fetch data after {max_retries} attempts: {response.text}")
                    return []

    except Exception as e:
        logging.error(f"Error fetching data from Space-Track.org: {str(e)}")
        return []
    finally:
        await client.aclose()

def process_space_objects(data):
    """Process raw space objects data into visualization format"""
    # Check if data is an error response
    if isinstance(data, dict):
        if 'error' in data:
            logging.error(f"Cannot process error response: {data['error']}")
            return None
        else:
            logging.error(f"Expected list of objects, got dictionary")
            return None
        
    if not isinstance(data, list):
        logging.error(f"Expected list of objects, got {type(data)}")
        return None
    
    if not data:  # Empty list
        logging.warning("No space objects data returned")
        return None
        
    processed_objects = []
    
    for obj in data:
        try:
            # Calculate position from orbital elements
            semi_major_axis = float(obj.get('SEMIMAJOR_AXIS', 0))
            eccentricity = float(obj.get('ECCENTRICITY', 0))
            inclination = float(obj.get('INCLINATION', 0))
            
            # Simple position calculation (this should be enhanced with proper orbital mechanics)
            radius = semi_major_axis * (1 - eccentricity)
            angle = (datetime.utcnow().timestamp() % 360) * (3.14159 / 180)
            
            position = {
                'x': radius * 0.0001 * math.cos(angle),  # Scale down for visualization
                'y': radius * 0.0001 * math.sin(angle) * math.cos(inclination * (3.14159 / 180)),
                'z': radius * 0.0001 * math.sin(angle) * math.sin(inclination * (3.14159 / 180))
            }
            
            # Determine object type and risk level
            is_debris = obj.get('OBJECT_TYPE', '').lower() in ['debris', 'unknown']
            
            processed_objects.append({
                'id': obj.get('NORAD_CAT_ID', ''),
                'type': 'debris' if is_debris else 'satellite',
                'position': position,
                'radius': 0.1 if is_debris else 0.15,  # Debris slightly smaller than satellites
                'inclination': inclination,
                'risk_level': calculate_risk_level(obj),
                'metadata': {
                    'origin': obj.get('OBJECT_NAME', 'Unknown'),
                    'estimated_mass': obj.get('MASS', 0),
                    'first_observed': obj.get('EPOCH', '')
                }
            })
        except Exception as e:
            logging.error(f"Error processing object {obj.get('NORAD_CAT_ID', 'unknown')}: {str(e)}")
            continue
    
    return processed_objects

def calculate_risk_level(obj):
    """Calculate risk level based on various parameters"""
    risk = 50  # Base risk
    
    # Adjust risk based on altitude
    perigee = float(obj.get('PERIGEE', 0))
    if perigee < 500:  # Low orbit, higher risk
        risk += 20
    elif perigee > 35000:  # Very high orbit, lower risk
        risk -= 20
    
    # Adjust risk based on object type
    if obj.get('OBJECT_TYPE', '').lower() == 'debris':
        risk += 15
    
    # Ensure risk is between 0 and 100
    return max(0, min(100, risk))

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logging.info("New WebSocket connection attempt")
    await websocket.accept()
    logging.info("WebSocket connection accepted")
    
    retry_count = 0
    max_retries = 3
    retry_delay = 60  # seconds
    rate_limit_backoff = 300  # 5 minutes
    
    try:
        while True:
            try:
                # First try to get data from cache
                space_objects = space_objects_cache.get()
                
                # If cache miss or expired, fetch new data
                if not space_objects:
                    space_objects = await fetch_space_objects()
                    
                    if space_objects:
                        space_objects_cache.set(space_objects)
                        logging.info(f"Updated cache with {len(space_objects)} objects")
                        retry_count = 0  # Reset retry count on success
                    else:
                        retry_count += 1
                        
                        # Check if we hit the rate limit
                        if isinstance(space_objects, dict) and 'error' in space_objects and 'rate limit' in space_objects['error'].lower():
                            logging.warning("Rate limit hit, backing off...")
                            await websocket.send_json({
                                'type': 'status',
                                'message': 'Rate limit exceeded. Waiting before next attempt...',
                                'timestamp': datetime.utcnow().isoformat()
                            })
                            await asyncio.sleep(rate_limit_backoff)
                            retry_count = 0  # Reset retry count after waiting
                            continue
                        
                        # Handle other errors
                        if retry_count >= max_retries:
                            logging.error("Failed to fetch data after maximum retries")
                            await websocket.send_json({
                                'type': 'error',
                                'message': 'Failed to fetch data after maximum retries. Please try again later.',
                                'timestamp': datetime.utcnow().isoformat()
                            })
                            await asyncio.sleep(retry_delay)
                            retry_count = 0  # Reset retry count
                            continue
                        
                        logging.warning(f"Failed to fetch new data, attempt {retry_count}/{max_retries}")
                        await websocket.send_json({
                            'type': 'status',
                            'message': f'Retrying data fetch ({retry_count}/{max_retries})...',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        await asyncio.sleep(5)
                        continue
                
                # Send data to client
                if space_objects:
                    await websocket.send_json({
                        'type': 'update',
                        'data': space_objects,
                        'timestamp': datetime.utcnow().isoformat(),
                        'count': len(space_objects)
                    })
                    logging.info(f"Sent update with {len(space_objects)} objects")
                else:
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'No data available',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    logging.warning("No space objects data available")
            except Exception as e:
                logging.error(f"Error during websocket operation: {str(e)}")
                try:
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'Internal server error, retrying...',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                except Exception as send_error:
                    logging.error(f"Failed to send error message: {str(send_error)}")
                    break
            
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected normally")
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()
        logging.info("WebSocket connection closed")

if __name__ == "__main__":
    import uvicorn
    import math  # Required for orbital calculations
    uvicorn.run(app, host="127.0.0.1", port=8000)
