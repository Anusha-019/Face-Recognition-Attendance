import face_recognition
import cv2
import numpy as np
import os
from typing import List, Tuple, Dict
from PIL import Image


class FaceUtils:
    def __init__(self, known_faces_dir: str = "known_faces"):
        self.known_faces_dir = known_faces_dir
        self.known_face_encodings = []
        self.known_face_names = []

        if not os.path.exists(self.known_faces_dir):
            os.makedirs(self.known_faces_dir)

        self.load_known_faces()

    def load_known_faces(self) -> None:
        """Load all known face encodings from the known_faces directory."""
        self.known_face_encodings = []
        self.known_face_names = []

        for filename in os.listdir(self.known_faces_dir):
            if filename.endswith((".jpg", ".jpeg", ".png")):
                path = os.path.join(self.known_faces_dir, filename)
                name = os.path.splitext(filename)[0]
                success = self.add_known_face(path, name)
                if not success:
                    print(f"[WARN] Failed to load face from: {path}")

        print(f"[INFO] Loaded {len(self.known_face_encodings)} known face(s)")

    def add_known_face(self, image_path: str, name: str) -> bool:
        """Add a new face encoding from image."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Image not found or unreadable")

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            if rgb_image.dtype != np.uint8:
                rgb_image = (255 * rgb_image).astype(np.uint8)

            encodings = face_recognition.face_encodings(rgb_image)
            if len(encodings) == 0:
                raise ValueError("No face found in image")

            self.known_face_encodings.append(encodings[0])
            self.known_face_names.append(name)
            return True

        except Exception as e:
            print(f"[ERROR] add_known_face({name}): {e}")
            return False

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        if frame is None:
            raise ValueError("Frame is None")

        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("Invalid frame format")

        if frame.dtype != np.uint8:
            frame = (255 * frame).astype(np.uint8)

        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        try:
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        except Exception as e:
            print(f"[ERROR] Face detection failed: {e}")
            return frame, []

        if not self.known_face_encodings:
            print("[WARN] No known faces loaded")

        face_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
            name = "Unknown"

            if True in matches:
                first_match_index = matches.index(True)
                name = self.known_face_names[first_match_index]

            face_names.append(name)

        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
            cv2.putText(frame, name, (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

        return frame, face_names

    def register_new_face(self, image_path: str, name: str) -> bool:
        """Register a new face from uploaded image."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Image could not be loaded")

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            if rgb_image.dtype != np.uint8:
                rgb_image = (255 * rgb_image).astype(np.uint8)

            face_locations = face_recognition.face_locations(rgb_image)
            if len(face_locations) != 1:
                print(f"[WARN] Detected {len(face_locations)} face(s) in image. Exactly one required.")
                return False

            save_path = os.path.join(self.known_faces_dir, f"{name}.jpg")
            Image.fromarray(rgb_image).save(save_path)

            added = self.add_known_face(save_path, name)
            return added

        except Exception as e:
            print(f"[ERROR] register_new_face({name}): {e}")
            return False
