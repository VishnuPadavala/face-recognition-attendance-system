import pickle
import logging
import shutil
import os

logger = logging.getLogger("UserManager")

class UserManager:
    """
    Manages user registration, details retrieval, deletion, and face encoding persistence.
    """
    def __init__(self, db_manager):
        self.db = db_manager

    def register_user(self, user_id, name, department, email=None):
        """
        Registers a new user (student/employee) in the database.
        Returns True on success, raises an Exception on failure.
        """
        # Validate input parameters
        if not user_id or not name or not department:
            raise ValueError("User ID, Name, and Department are required fields.")

        # Clean inputs
        user_id = user_id.strip()
        name = name.strip()
        department = department.strip()
        email = email.strip() if email else None

        query = """
            INSERT INTO users (user_id, name, department, email)
            VALUES (?, ?, ?, ?)
        """
        try:
            self.db.execute_query(query, (user_id, name, department, email), commit=True)
            logger.info(f"User '{name}' (ID: {user_id}) registered successfully in database.")
            return True
        except Exception as e:
            logger.error(f"Failed to register user in database: {e}")
            raise

    def add_face_encoding(self, user_id, encoding_vector):
        """
        Saves a 128-dimensional face encoding vector linked to a user.
        Serializes the numpy array as a binary BLOB using pickle.
        """
        if encoding_vector is None:
            raise ValueError("Encoding vector cannot be None.")

        # Serialize encoding vector
        binary_encoding = pickle.dumps(encoding_vector)

        query = """
            INSERT INTO face_encodings (user_id, encoding)
            VALUES (?, ?)
        """
        try:
            self.db.execute_query(query, (user_id, binary_encoding), commit=True)
            logger.info(f"Face encoding added for user {user_id}.")
            return True
        except Exception as e:
            logger.error(f"Failed to save face encoding for user {user_id}: {e}")
            raise

    def get_user(self, user_id):
        """
        Retrieves details of a single user by User ID.
        Returns a dict-like Row or None.
        """
        query = "SELECT * FROM users WHERE user_id = ?"
        try:
            return self.db.fetch_one(query, (user_id,))
        except Exception as e:
            logger.error(f"Failed to retrieve user {user_id}: {e}")
            return None

    def get_all_users(self):
        """
        Retrieves all registered users.
        Returns a list of dict-like Rows.
        """
        query = "SELECT * FROM users ORDER BY created_at DESC"
        try:
            return self.db.fetch_all(query)
        except Exception as e:
            logger.error(f"Failed to retrieve users list: {e}")
            return []

    def get_all_encodings(self):
        """
        Fetches all face encodings from database, deserializing the BLOBs back into numpy arrays.
        Returns a dictionary mapping user_id to a list of numpy arrays: {user_id: [array1, array2, ...]}
        """
        query = "SELECT user_id, encoding FROM face_encodings"
        encodings_map = {}
        try:
            rows = self.db.fetch_all(query)
            for row in rows:
                user_id = row['user_id']
                try:
                    encoding = pickle.loads(row['encoding'])
                    if user_id not in encodings_map:
                        encodings_map[user_id] = []
                    encodings_map[user_id].append(encoding)
                except Exception as ex:
                    logger.error(f"Failed to deserialize face encoding for user {user_id}: {ex}")
            return encodings_map
        except Exception as e:
            logger.error(f"Failed to retrieve face encodings: {e}")
            return {}

    def delete_user(self, user_id):
        """
        Deletes a user from the database. This cascades and deletes their face encodings as well.
        Also deletes their face images directory from static storage.
        """
        query = "DELETE FROM users WHERE user_id = ?"
        try:
            # Delete from DB
            self.db.execute_query(query, (user_id,), commit=True)
            logger.info(f"User {user_id} deleted from database.")

            # Delete physical face photos if directory exists
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            user_faces_dir = os.path.join(project_root, "static", "faces", user_id)
            if os.path.exists(user_faces_dir):
                shutil.rmtree(user_faces_dir)
                logger.info(f"Deleted face directory for user {user_id}: {user_faces_dir}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise
