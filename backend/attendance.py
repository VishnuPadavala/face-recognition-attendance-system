import csv
import logging
import sqlite3
import os

logger = logging.getLogger("AttendanceManager")

class AttendanceManager:
    """
    Manages logging, querying, and exporting attendance records.
    """
    def __init__(self, db_manager):
        self.db = db_manager

    def mark_attendance(self, user_id, date_str, time_str, status="Present"):
        """
        Marks attendance for a user on a specific date and time.
        Enforces once-per-day limit.
        Returns:
            (bool, str): (True, message) if marked successfully, (False, reason) otherwise.
        """
        user_id = user_id.strip()
        date_str = date_str.strip()
        time_str = time_str.strip()

        # 1. Check if attendance already exists for this user on this day
        check_query = "SELECT 1 FROM attendance WHERE user_id = ? AND date = ?"
        try:
            exists = self.db.fetch_one(check_query, (user_id, date_str))
            if exists:
                logger.info(f"Attendance already marked for {user_id} on {date_str}. Skipping insert.")
                return False, "Already marked today"

            # 2. Insert new attendance record
            insert_query = """
                INSERT INTO attendance (user_id, date, time, status)
                VALUES (?, ?, ?, ?)
            """
            self.db.execute_query(insert_query, (user_id, date_str, time_str, status), commit=True)
            logger.info(f"Attendance marked: User {user_id} on {date_str} at {time_str}.")
            return True, "Success"
            
        except sqlite3.IntegrityError as ie:
            # Handle integrity error (such as unique constraint violation on unique(user_id, date))
            logger.warning(f"Integrity constraint hit while marking attendance: {ie}")
            return False, "Already marked today"
        except Exception as e:
            logger.error(f"Error marking attendance for user {user_id}: {e}")
            return False, f"Database error: {e}"

    def get_attendance_records(self, date_filter=None, user_id=None):
        """
        Retrieves attendance records joined with user details.
        Optionally filters by date (YYYY-MM-DD) or user_id.
        Returns a list of dict-like Rows.
        """
        query = """
            SELECT a.id, a.user_id, u.name, u.department, a.date, a.time, a.status 
            FROM attendance a 
            JOIN users u ON a.user_id = u.user_id
        """
        params = []
        conditions = []

        if date_filter:
            conditions.append("a.date = ?")
            params.append(date_filter)
        if user_id:
            conditions.append("a.user_id = ?")
            params.append(user_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Order by most recent records
        query += " ORDER BY a.date DESC, a.time DESC"

        try:
            return self.db.fetch_all(query, tuple(params))
        except Exception as e:
            logger.error(f"Failed to fetch attendance records: {e}")
            return []

    def export_attendance_to_csv(self, file_path, date_filter=None):
        """
        Exports attendance records to a CSV file.
        Returns:
            (bool, str): (True, file_path) if successful, (False, error_message) otherwise.
        """
        try:
            records = self.get_attendance_records(date_filter=date_filter)
            
            # Ensure target folder exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(["Record ID", "User ID", "Name", "Department", "Date", "Time", "Status"])
                
                # Write data rows
                for r in records:
                    writer.writerow([
                        r['id'],
                        r['user_id'],
                        r['name'],
                        r['department'],
                        r['date'],
                        r['time'],
                        r['status']
                    ])
            
            logger.info(f"Attendance exported to CSV successfully at {file_path}")
            return True, file_path
        except Exception as e:
            logger.error(f"Failed to export attendance to CSV: {e}")
            return False, str(e)
