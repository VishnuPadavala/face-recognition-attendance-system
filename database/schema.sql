-- schema.sql
-- Database schema setup for Face Recognition Attendance System

-- Create Users table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Face Encodings table to store 128-dimensional vectors as BLOBs
CREATE TABLE IF NOT EXISTS face_encodings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    encoding BLOB NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- Create Attendance table enforcing one record per user per day
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    date TEXT NOT NULL,          -- Format: YYYY-MM-DD
    time TEXT NOT NULL,          -- Format: HH:MM:SS
    status TEXT NOT NULL,        -- e.g., 'Present'
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    UNIQUE(user_id, date)        -- Prevents multiple check-ins per day
);
