import os
import sqlite3
import logging

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DatabaseManager")

class DatabaseManager:
    """
    Manages connections and operations for the SQLite database.
    """
    def __init__(self, db_path=None):
        if db_path is None:
            # Resolve db path relative to the project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, "database", "attendance.db")
        
        self.db_path = db_path
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        logger.info(f"DatabaseManager initialized with path: {self.db_path}")

    def _get_connection(self):
        """
        Establishes a connection to the database. Sets row_factory to sqlite3.Row 
        so results can be accessed like dictionaries.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            # Enable Foreign Key constraints
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def initialize_database(self, schema_path=None):
        """
        Reads and executes the SQL schema script to set up database tables.
        """
        if schema_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            schema_path = os.path.join(project_root, "database", "schema.sql")

        if not os.path.exists(schema_path):
            logger.error(f"Schema file not found at {schema_path}")
            return False

        try:
            with open(schema_path, 'r') as f:
                schema_sql = f.read()

            with self._get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()
            
            logger.info("Database schema initialized successfully.")
            return True
        except (sqlite3.Error, IOError) as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    def execute_query(self, query, params=(), commit=False):
        """
        Executes a query (INSERT, UPDATE, DELETE) and optionally commits the transaction.
        Returns the last row ID (for INSERTs) or the number of rows affected.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            lastrowid = cursor.lastrowid
            rowcount = cursor.rowcount
            
            if commit:
                conn.commit()
                
            return lastrowid if lastrowid else rowcount
        except sqlite3.Error as e:
            logger.error(f"Database error executing query: {query} | Error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def fetch_all(self, query, params=()):
        """
        Fetches all rows resulting from a SELECT query.
        Returns a list of sqlite3.Row objects (access like dict).
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Database error executing fetch_all: {query} | Error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def fetch_one(self, query, params=()):
        """
        Fetches a single row resulting from a SELECT query.
        Returns sqlite3.Row object or None.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Database error executing fetch_one: {query} | Error: {e}")
            raise
        finally:
            if conn:
                conn.close()
