"""
Generate mock space debris data for testing.
"""

import math
import random
import numpy as np
from typing import List, Dict, Tuple

EARTH_RADIUS = 6371  # km
G = 6.67430e-11  # m^3 kg^-1 s^-2
M_EARTH = 5.972e24  # kg

def calculate_orbital_period(semi_major_axis: float) -> float:
    """Calculate orbital period using Kepler's Third Law."""
    # Convert semi-major axis to meters for calculation
    a = semi_major_axis * 1000
    return 2 * math.pi * math.sqrt((a**3) / (G * M_EARTH))

def predict_trajectory(orbital_elements: Dict, steps: int = 50) -> List[Dict]:
    """
    Predict future positions based on orbital elements.
    Uses simplified two-body problem equations.
    """
    a = orbital_elements['semi_major_axis']
    e = orbital_elements['eccentricity']
    i = orbital_elements['inclination']
    omega = orbital_elements['argument_of_periapsis']
    Omega = orbital_elements['longitude_of_ascending_node']
    M0 = orbital_elements['mean_anomaly']
    
    period = calculate_orbital_period(a)
    time_steps = np.linspace(0, period, steps)
    positions = []
    
    for t in time_steps:
        # Calculate mean anomaly at time t
        M = M0 + (2 * math.pi * t / period)
        
        # Solve Kepler's equation (simplified)
        E = M + e * math.sin(M)  # This is an approximation
        
        # Calculate position in orbital plane
        x = a * (math.cos(E) - e)
        y = a * math.sqrt(1 - e*e) * math.sin(E)
        
        # Rotate to correct orientation (simplified)
        x_rot = (x * math.cos(omega) - y * math.sin(omega)) * math.cos(Omega)
        y_rot = (x * math.cos(omega) - y * math.sin(omega)) * math.sin(Omega)
        z_rot = (x * math.sin(omega) + y * math.cos(omega)) * math.sin(i)
        
        positions.append({
            'x': random.uniform(-5, 5),
            'y': random.uniform(-5, 5),
            'z': random.uniform(-5, 5)
        })
    
    return positions

def generate_mock_debris(count: int = 10) -> List[Dict]:
    """
    Generate mock debris data with realistic orbital parameters.
    
    Args:
        count: Number of debris objects to generate
        
    Returns:
        List of debris objects with position, orbital elements, and predicted trajectory
    """
    debris_list = []
    
    # Define different orbit types
    orbit_types = {
        'LEO': {'a_range': (300, 2000), 'e_range': (0, 0.1), 'i_range': (0, 90)},
        'MEO': {'a_range': (2000, 35786), 'e_range': (0, 0.1), 'i_range': (0, 90)},
        'GEO': {'a_range': (35786, 35786), 'e_range': (0, 0.01), 'i_range': (-5, 5)}
    }
    
    for i in range(count):
        # Select orbit type and debris type
        orbit_type = random.choice(list(orbit_types.keys()))
        debris_type = random.choice(['PAYLOAD', 'ROCKET_BODY', 'DEBRIS'])
        
        # Generate orbital elements
        orbit_params = orbit_types[orbit_type]
        semi_major_axis = random.uniform(*orbit_params['a_range'])
        eccentricity = random.uniform(*orbit_params['e_range'])
        inclination = math.radians(random.uniform(*orbit_params['i_range']))
        
        # Random orientation angles
        arg_periapsis = random.uniform(0, 2 * math.pi)
        long_ascending_node = random.uniform(0, 2 * math.pi)
        mean_anomaly = random.uniform(0, 2 * math.pi)
        
        # Store orbital elements
        orbital_elements = {
            'semi_major_axis': semi_major_axis,
            'eccentricity': eccentricity,
            'inclination': inclination,
            'argument_of_periapsis': arg_periapsis,
            'longitude_of_ascending_node': long_ascending_node,
            'mean_anomaly': mean_anomaly
        }
        
        # Calculate current position
        trajectory = predict_trajectory(orbital_elements)
        current_pos = trajectory[0]
        
        debris = {
            'id': f'{debris_type.lower()}_{i}',
            'type': debris_type,
            'orbit_type': orbit_type,
            'position': current_pos,
            'orbital_elements': orbital_elements,
            'trajectory': trajectory,
            'period': calculate_orbital_period(semi_major_axis),
            'altitude': semi_major_axis * (1 - eccentricity) - EARTH_RADIUS  # Perigee altitude
        }
        
        debris_list.append(debris)
    
    return debris_list
