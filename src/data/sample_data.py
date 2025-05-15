"""Generate sample space debris data for visualization."""
import numpy as np
from datetime import datetime, timedelta
import math

class DebrisGenerator:
    def __init__(self):
        # Constants for Earth orbit (all in km)
        self.EARTH_RADIUS = 6371.0  # Earth's radius in km
        self.LEO_MIN = 160  # Low Earth Orbit minimum altitude in km
        self.LEO_MAX = 2000  # Low Earth Orbit maximum altitude in km
        self.VISUALIZATION_SCALE = 1/6371.0  # Scale everything relative to Earth's radius
        
    def generate_orbit_parameters(self):
        """Generate random orbital parameters."""
        # Random altitude between LEO_MIN and LEO_MAX (in km)
        altitude = np.random.uniform(self.LEO_MIN, self.LEO_MAX)
        radius = self.EARTH_RADIUS + altitude  # Total radius in km
        
        # Random inclination (angle with equatorial plane)
        inclination = np.random.uniform(0, 180)
        
        # Random phase angle
        phase = np.random.uniform(0, 360)
        
        return radius, inclination, phase
    
    def calculate_position(self, radius, inclination, phase, time_offset):
        """Calculate position based on orbital parameters."""
        # Convert angles to radians
        inclination_rad = math.radians(inclination)
        phase_rad = math.radians(phase)
        
        # Calculate orbital period (in minutes) using Kepler's Third Law
        period = 2 * math.pi * math.sqrt(radius**3 / (398600.4418 * 60**2))  # GM of Earth
        
        # Calculate current angle based on time
        angle = (2 * np.pi * time_offset / period) % (2 * np.pi)
            
        # Scale orbit radius to be relative to Earth radius but larger for visibility
        orbit_radius = random.uniform(2.2, 4.0)  # Between 2.2 and 4.0 Earth radii
        
        # Calculate 3D position
        x = orbit_radius * np.cos(angle) * np.cos(inclination_rad)
        y = orbit_radius * np.sin(angle)
        z = orbit_radius * np.cos(angle) * np.sin(inclination_rad)
        
        # Scale for visualization
        x *= self.VISUALIZATION_SCALE
        y *= self.VISUALIZATION_SCALE
        z *= self.VISUALIZATION_SCALE
        
        return x, y, z
    
    def generate_debris(self, num_objects=50):
        """Generate a list of debris objects with their parameters."""
        debris_objects = []
        
        for i in range(num_objects):
            radius, inclination, phase = self.generate_orbit_parameters()
            
            # Generate random size and risk level
            size = np.random.uniform(0.1, 2.0)  # meters
            risk_level = np.random.uniform(0, 100)  # percentage
            
            debris = {
                "id": f"debris_{i}",
                "type": "debris",
                "radius": radius,
                "inclination": inclination,
                "phase": phase,
                "size": size,
                "risk_level": risk_level,
                "metadata": {
                    "origin": "Sample Data",
                    "estimated_mass": size * 100,  # kg, rough estimation
                    "first_observed": (datetime.now() - timedelta(days=np.random.randint(1, 365))).isoformat()
                }
            }
            debris_objects.append(debris)
        
        return debris_objects
    
    def generate_satellites(self, num_objects=10):
        """Generate a list of active satellite objects."""
        satellites = []
        
        for i in range(num_objects):
            radius, inclination, phase = self.generate_orbit_parameters()
            
            satellite = {
                "id": f"satellite_{i}",
                "type": "satellite",
                "radius": radius,
                "inclination": inclination,
                "phase": phase,
                "size": np.random.uniform(1.0, 5.0),  # meters
                "metadata": {
                    "name": f"SAT-{i:03d}",
                    "operator": np.random.choice(["SpaceX", "NASA", "ESA", "JAXA", "Roscosmos"]),
                    "launch_date": (datetime.now() - timedelta(days=np.random.randint(1, 1825))).isoformat()
                }
            }
            satellites.append(satellite)
        
        return satellites
    
    def update_positions(self, objects, time_offset):
        """Update positions of all objects based on time offset."""
        updated_objects = []
        
        for obj in objects:
            x, y, z = self.calculate_position(
                obj["radius"],
                obj["inclination"],
                obj["phase"],
                time_offset
            )
            
            # Calculate future positions for trajectory prediction
            future_positions = []
            for t in range(1, 11):  # Predict 10 future positions
                fx, fy, fz = self.calculate_position(
                    obj["radius"],
                    obj["inclination"],
                    obj["phase"],
                    time_offset + t * 10
                )
                future_positions.append({"x": fx, "y": fy, "z": fz})
            
            updated_obj = {
                "id": obj["id"],
                "type": obj["type"],
                "position": {"x": x, "y": y, "z": z},
                "prediction": future_positions
            }
            
            # Add additional properties based on object type
            if obj["type"] == "debris":
                updated_obj["risk_level"] = obj["risk_level"]
                updated_obj["size"] = obj["size"]
            
            updated_objects.append(updated_obj)
        
        return updated_objects
