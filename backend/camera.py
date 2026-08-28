import cv2
import threading
import time
import logging

logger = logging.getLogger("VideoCamera")

class VideoCamera:
    """
    Spawns a background thread to continuously read frames from the webcam.
    Prevents thread blocking and camera initialization lag in Flask routes.
    """
    _instance = None
    _lock = threading.Lock()
    _ref_count = 0  # Reference count to know when to release the camera

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VideoCamera, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, camera_index=0):
        with self._lock:
            if self._initialized:
                self._ref_count += 1
                return
            
            self.camera_index = camera_index
            self.video = cv2.VideoCapture(self.camera_index)
            
            # Set resolution (optional but good for performance)
            self.video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self.grabbed, self.frame = self.video.read()
            
            if not self.grabbed:
                logger.error(f"Could not open webcam at index {self.camera_index}")
                # Release immediately if it failed to grab
                self.video.release()
                raise RuntimeError("Webcam not accessible.")

            self.is_running = True
            self.last_access_time = time.time()
            self.frame_lock = threading.Lock()
            
            # Start background thread
            self.thread = threading.Thread(target=self._update, args=())
            self.thread.daemon = True
            self.thread.start()
            
            self._ref_count = 1
            self._initialized = True
            logger.info("VideoCamera background thread started successfully.")

    def _update(self):
        """
        Continuously grabs frames from the camera.
        """
        while self.is_running:
            grabbed, frame = self.video.read()
            if grabbed:
                with self.frame_lock:
                    self.grabbed = grabbed
                    self.frame = frame
            # 30 FPS sleep
            time.sleep(0.033)

    def get_frame(self):
        """
        Retrieves the latest frame from the webcam.
        """
        self.last_access_time = time.time()
        with self.frame_lock:
            if not self.grabbed or self.frame is None:
                return None
            return self.frame.copy()

    def release(self):
        """
        Decrements the reference count. If 0, stops the thread and releases the webcam.
        """
        with self._lock:
            self._ref_count -= 1
            logger.info(f"VideoCamera reference decremented. Active refs: {self._ref_count}")
            if self._ref_count <= 0:
                self.is_running = False
                # Allow update thread to exit
                time.sleep(0.1)
                if hasattr(self, 'video') and self.video.isOpened():
                    self.video.release()
                VideoCamera._instance = None
                self._initialized = False
                logger.info("VideoCamera fully released and shutdown.")
                
    @classmethod
    def get_instance(cls):
        """
        Retrieves the existing instance of VideoCamera, or returns None if inactive.
        """
        with cls._lock:
            return cls._instance
