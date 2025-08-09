import cv2
import dlib
import numpy as np
from scipy.spatial import distance as dist
from collections import OrderedDict
import time

class LivenessDetector:
    def __init__(self):
        # Initialize dlib's face detector and facial landmark predictor
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        
        # Define constants for eye aspect ratio (EAR)
        self.EYE_AR_THRESH = 0.3
        self.EYE_AR_CONSEC_FRAMES = 3
        
        # Initialize eye landmarks
        self.LEFT_EYE_IDXS = list(range(42, 48))
        self.RIGHT_EYE_IDXS = list(range(36, 42))
        
        # Initialize counters
        self.counter = 0
        self.total_blinks = 0
        self.last_blink_time = time.time()
        
    def eye_aspect_ratio(self, eye):
        """Calculate eye aspect ratio."""
        # Compute the euclidean distances between the vertical eye landmarks
        A = dist.euclidean(eye[1], eye[5])
        B = dist.euclidean(eye[2], eye[4])
        
        # Compute the euclidean distance between the horizontal eye landmarks
        C = dist.euclidean(eye[0], eye[3])
        
        # Compute the eye aspect ratio
        ear = (A + B) / (2.0 * C)
        return ear
        
    def get_landmarks(self, frame, face_rect):
        """Get facial landmarks for a detected face."""
        shape = self.predictor(frame, face_rect)
        coords = np.zeros((68, 2), dtype=int)
        
        for i in range(0, 68):
            coords[i] = (shape.part(i).x, shape.part(i).y)
            
        return coords
        
    def detect_blink(self, frame, face_rect):
        """Detect eye blinks in the frame."""
        landmarks = self.get_landmarks(frame, face_rect)
        
        # Extract eye coordinates
        leftEye = landmarks[self.LEFT_EYE_IDXS]
        rightEye = landmarks[self.RIGHT_EYE_IDXS]
        
        # Calculate eye aspect ratios
        leftEAR = self.eye_aspect_ratio(leftEye)
        rightEAR = self.eye_aspect_ratio(rightEye)
        
        # Average the eye aspect ratio for both eyes
        ear = (leftEAR + rightEAR) / 2.0
        
        # Check if eye aspect ratio is below the threshold
        if ear < self.EYE_AR_THRESH:
            self.counter += 1
        else:
            if self.counter >= self.EYE_AR_CONSEC_FRAMES:
                self.total_blinks += 1
                self.last_blink_time = time.time()
            self.counter = 0
            
        return leftEye, rightEye, ear
        
    def check_liveness(self, frame):
        """Check if the face in frame is live based on eye blinks."""
        # Convert frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.detector(gray, 0)
        
        result = {
            "is_live": False,
            "message": "No face detected",
            "debug_frame": frame.copy()
        }
        
        for face in faces:
            try:
                # Detect blinks
                leftEye, rightEye, ear = self.detect_blink(gray, face)
                
                # Draw eye contours
                debug_frame = frame.copy()
                leftEyeHull = cv2.convexHull(leftEye)
                rightEyeHull = cv2.convexHull(rightEye)
                cv2.drawContours(debug_frame, [leftEyeHull], -1, (0, 255, 0), 1)
                cv2.drawContours(debug_frame, [rightEyeHull], -1, (0, 255, 0), 1)
                
                # Check liveness conditions
                time_since_last_blink = time.time() - self.last_blink_time
                
                # Draw EAR and blink count
                cv2.putText(debug_frame, f"EAR: {ear:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(debug_frame, f"Blinks: {self.total_blinks}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Consider face live if we detect blinks
                if self.total_blinks > 0 and time_since_last_blink < 3.0:
                    result = {
                        "is_live": True,
                        "message": "Live face detected",
                        "debug_frame": debug_frame
                    }
                else:
                    result = {
                        "is_live": False,
                        "message": "Please blink naturally",
                        "debug_frame": debug_frame
                    }
                    
            except Exception as e:
                result = {
                    "is_live": False,
                    "message": f"Error in liveness detection: {str(e)}",
                    "debug_frame": frame
                }
                
        return result
        
    def reset(self):
        """Reset blink detection counters."""
        self.counter = 0
        self.total_blinks = 0
        self.last_blink_time = time.time() 