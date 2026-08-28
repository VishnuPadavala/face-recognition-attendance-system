import cv2
import logging

logger = logging.getLogger("FaceDetector")

class FaceDetector:
    """
    Handles face detection within camera frames using OpenCV's Haar Cascade classifier.
    """
    def __init__(self):
        # Load OpenCV's pre-trained Haar Cascade classifier for frontal face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if self.face_cascade.empty():
            logger.error("Failed to load Haar Cascade face detection model.")
            raise RuntimeError("Could not load Haar Cascade XML file.")
        
        logger.info("FaceDetector successfully initialized with Haar Cascade.")

    def detect_faces(self, frame):
        """
        Detects faces in the given BGR image frame.
        Returns a list of bounding boxes: [(x, y, w, h), ...]
        """
        if frame is None:
            return []

        try:
            # Convert frame to grayscale (Haar Cascade operates on grayscale images)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces with tuned parameters for a balance between speed and accuracy
            # scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            # Returns a list of tuples/lists containing [x, y, w, h]
            return list(faces)
        except Exception as e:
            logger.error(f"Error during face detection: {e}")
            return []
