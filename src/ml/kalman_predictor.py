"""Kalman filter for debris trajectory prediction."""
import numpy as np
from filterpy.kalman import KalmanFilter
from typing import Tuple, List

class DebrisKalmanPredictor:
    def __init__(self):
        # State: [x, y, z, vx, vy, vz]
        self.kf = KalmanFilter(dim_x=6, dim_z=3)
        self.initialized = False
        
    def initialize_filter(self, initial_state: np.ndarray):
        """Initialize the Kalman filter with first position measurement."""
        dt = 1.0  # Time step
        
        # State transition matrix
        self.kf.F = np.array([
            [1, 0, 0, dt, 0, 0],
            [0, 1, 0, 0, dt, 0],
            [0, 0, 1, 0, 0, dt],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ])
        
        # Measurement matrix (we only measure position)
        self.kf.H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ])
        
        # Initial state
        self.kf.x = np.zeros(6)
        self.kf.x[:3] = initial_state
        
        self.initialized = True
    
    def update(self, measurement: np.ndarray) -> np.ndarray:
        """Update the filter with a new measurement."""
        if not self.initialized:
            self.initialize_filter(measurement)
            return self.kf.x[:3]
        
        self.kf.predict()
        self.kf.update(measurement)
        return self.kf.x[:3]
    
    def predict_future_positions(self, steps: int) -> List[Tuple[float, float, float]]:
        """Predict future positions for the specified number of steps."""
        if not self.initialized:
            raise ValueError("Kalman filter not initialized")
        
        predictions = []
        state = self.kf.x.copy()
        
        for _ in range(steps):
            state = np.dot(self.kf.F, state)
            predictions.append(tuple(state[:3]))
        
        return predictions
