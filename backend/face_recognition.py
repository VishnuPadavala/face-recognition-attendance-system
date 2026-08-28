import face_recognition
import numpy as np
import logging

logger = logging.getLogger("FaceRecognizer")

class FaceRecognizer:
    """
    Handles face encoding extraction and matching using dlib's face_recognition model.
    """
    def __init__(self, tolerance=0.6):
        # Match tolerance: lower is stricter, higher is more forgiving
        # 0.6 is the standard recommended threshold for face_recognition
        self.tolerance = tolerance
        logger.info(f"FaceRecognizer initialized with tolerance: {self.tolerance}")

    def cv2_box_to_css(self, box):
        """
        Converts OpenCV bounding box (x, y, w, h) to face_recognition CSS box (top, right, bottom, left).
        """
        x, y, w, h = box
        return (y, x + w, y + h, x)

    def get_face_encodings(self, rgb_frame, cv2_boxes=None):
        """
        Extracts 128-dimensional encodings for all faces in the frame.
        If cv2_boxes is provided, uses them to extract encodings. Otherwise, uses HOG.
        """
        try:
            face_locations = None
            if cv2_boxes:
                # Convert all OpenCV boxes to CSS format
                face_locations = [self.cv2_box_to_css(box) for box in cv2_boxes]
            
            # Generate encodings
            encodings = face_recognition.face_encodings(rgb_frame, known_face_locations=face_locations)
            return encodings
        except Exception as e:
            logger.error(f"Error extracting face encodings: {e}")
            return []

    def match_face(self, face_encoding, known_encodings_map):
        """
        Compares a query face encoding with all known face encodings.
        known_encodings_map: dict mapping user_id to lists of numpy array encodings:
                             { 'U001': [array1, array2...], 'U002': [array...] }
        Returns: user_id of the best match if matches are found within tolerance, otherwise None.
        """
        if not known_encodings_map:
            return None

        try:
            # Flatten map into parallel lists
            flat_encodings = []
            flat_user_ids = []
            
            for user_id, encodings in known_encodings_map.items():
                for enc in encodings:
                    flat_encodings.append(enc)
                    flat_user_ids.append(user_id)

            if not flat_encodings:
                return None

            # Calculate Euclidean distances between the query encoding and all registered encodings
            distances = face_recognition.face_distance(flat_encodings, face_encoding)
            
            # Find the index of the minimum distance
            min_dist_idx = np.argmin(distances)
            min_distance = distances[min_dist_idx]

            # If the best match is within tolerance, we have identified the user
            if min_distance <= self.tolerance:
                matched_user = flat_user_ids[min_dist_idx]
                logger.info(f"Match found: {matched_user} (distance: {min_distance:.4f})")
                return matched_user
            
            logger.info(f"No match found. Closest distance was {min_distance:.4f} (tolerance: {self.tolerance})")
            return None

        except Exception as e:
            logger.error(f"Error during face matching: {e}")
            return None
