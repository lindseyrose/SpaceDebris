"""
Generate mock data for space debris visualization.
"""

import random
import math

def generate_orbital_elements():
    """Generate realistic orbital elements."""
    return {
        'semi_major_axis': random.uniform(6800, 42000),  # km from Earth's center
        'eccentricity': random.uniform(0, 0.3),
        'inclination': random.uniform(0, 180),
        'argument_of_periapsis': random.uniform(0, 360),
        'longitude_of_ascending_node': random.uniform(0, 360),
        'mean_anomaly': random.uniform(0, 360)
    }

def calculate_position(orbital_elements, time=0):
    """Calculate position based on orbital elements."""
    a = orbital_elements['semi_major_axis']
    e = orbital_elements['eccentricity']
    i = math.radians(orbital_elements['inclination'])
    omega = math.radians(orbital_elements['argument_of_periapsis'])
    Omega = math.radians(orbital_elements['longitude_of_ascending_node'])
    M = math.radians(orbital_elements['mean_anomaly'] + time)
    
    # Solve Kepler's equation (simplified)
    E = M + e * math.sin(M)
    
    # Calculate position in orbital plane
    x = a * (math.cos(E) - e)
    y = a * math.sqrt(1 - e*e) * math.sin(E)
    z = 0
    
    # Rotate to correct orientation
    # First rotate around z by omega
    x1 = x * math.cos(omega) - y * math.sin(omega)
    y1 = x * math.sin(omega) + y * math.cos(omega)
    z1 = z
    
    # Then rotate around x by i
    x2 = x1
    y2 = y1 * math.cos(i) - z1 * math.sin(i)
    z2 = y1 * math.sin(i) + z1 * math.cos(i)
    
    # Finally rotate around z by Omega
    x3 = x2 * math.cos(Omega) - y2 * math.sin(Omega)
    y3 = x2 * math.sin(Omega) + y2 * math.cos(Omega)
    z3 = z2
    
    # Scale down for visualization
    scale = 0.001  # Reduced scale for better visibility
    return {
        'x': x3 * scale,
        'y': y3 * scale,
        'z': z3 * scale
    }

def generate_mock_debris(count=100):
    """Generate mock space debris and satellite data."""
    objects = []
    
    # Common satellite types and their characteristics
    satellite_types = [
        'communication',
        'navigation',
        'earth_observation',
        'weather',
        'military'
    ]
    
    for i in range(count):
        try:
            # Determine if this is debris or a satellite (30% chance of being a satellite)
            is_satellite = random.random() < 0.3
            
            orbital_elements = generate_orbital_elements()
            position = calculate_position(orbital_elements)
            
            if not all(isinstance(p, (int, float)) for p in position):
                continue  # Skip if position contains non-numeric values
            
            if is_satellite:
                obj_type = 'satellite'
                subtype = random.choice(satellite_types)
            else:
                obj_type = 'debris'
                subtype = random.choice(['rocket_body', 'fragment', 'defunct_satellite'])
        except Exception as e:
            print(f'Error generating object {i}: {e}')
            continue
        
        # Calculate orbital period (simplified)
        period = 2 * math.pi * math.sqrt(pow(orbital_elements['semi_major_axis'], 3) / 398600.4418)  # in seconds
        
        # Generate trajectory points
        trajectory = []
        points = 100
        for t in range(points):
            time = (t / points) * period
            pos = calculate_position(orbital_elements, time)
            trajectory.append(pos)
        
        objects.append({
            'id': f'{"SAT" if is_satellite else "DEB"}-{i:04d}',
            'type': obj_type,
            'subtype': subtype,

            'position': position,
            'orbital_elements': orbital_elements,
            'period': period,
            'trajectory': trajectory,
            'launch_date': f'202{random.randint(0,4)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
            'status': 'active' if is_satellite else 'inactive'
        })
    
    return objects
