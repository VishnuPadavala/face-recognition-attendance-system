# AI-Based Face Recognition Attendance System

A production-ready, clean, and modern Face Recognition Attendance System built in Python using **Flask**, **OpenCV**, and the **dlib-based `face_recognition`** library.

This application provides a highly polished, glassmorphism dark-mode web dashboard where administrators can register employees/students, track attendance in real time via their webcam, query records, and download attendance reports.

---

## 🌟 Key Features

* **Biometric Registration**: Input profile details and capture 5 facial poses sequentially through a live webcam stream to enroll new users.
* **128-Dimensional Face Encodings**: Generates precise face vector mappings and persists them as serialized SQLite BLOBs.
* **Real-Time Detection & Matching**: Uses OpenCV Haar Cascade for swift CPU-friendly face detection and overlays a green bounding box with the user's name for matches, or a red bounding box for unrecognized ("Unknown") individuals.
* **Once-Per-Day Attendance Constraint**: Automatically records attendance only once per user per calendar day to avoid duplicate scan entries.
* **Modern Web Dashboard**: Features live statistics (attendance rate, active users, check-in count) and real-time logs updated via background AJAX polling.
* **History Queries & Reports**: Search and filter attendance logs by specific dates, and download CSV reports immediately.
* **Robust Threaded Video Capture**: Uses a background thread reader for webcam frames to eliminate camera initialization lag and UI freezes.

---

## 📂 Project Directory Structure

```
face_recognition_attendance/
├── app.py                      # Main Flask application and routing controller
├── requirements.txt            # Python dependencies lists
├── README.md                   # Project documentation and guide
├── backend/
│   ├── __init__.py
│   ├── camera.py               # Threaded camera frame grabber
│   ├── face_detection.py       # Wrapper for OpenCV Haar Cascade face detector
│   ├── face_recognition.py     # Wrapper for dlib face feature mapping & matching
│   ├── attendance.py           # Database logger & CSV exporter for attendance
│   ├── database.py             # SQLite helper executing query transactions
│   └── user.py                 # User creation, deletion, and encoding loader
├── database/
│   ├── schema.sql              # SQL script initializing SQLite tables
│   └── attendance.db           # SQLite database file (generated at runtime)
├── static/
│   ├── css/
│   │   └── style.css           # Premium glassmorphic dark CSS stylesheet
│   ├── js/
│   │   └── main.js             # Async capture sequences and logs polling
│   └── faces/                  # Saved photos of registered users (created at runtime)
└── templates/
    ├── base.html               # Shared navigation layout
    ├── dashboard.html          # Stats card grid and recent logs
    ├── register.html           # User details input and camera captures
    ├── attendance_cam.html     # Active video scan feed and live updates table
    ├── users.html              # List of registered database accounts
    └── records.html            # Attendance log search and CSV downloads
```

---

## 🛠️ Database Schema

The SQLite database (`database/attendance.db`) initializes automatically with three primary tables:

### 1. `users`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | TEXT | PRIMARY KEY | Unique Employee or Student ID |
| `name` | TEXT | NOT NULL | User's full name |
| `department` | TEXT | NOT NULL | Target class/department |
| `email` | TEXT | NULL | Optional email address |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |

### 2. `face_encodings`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique record ID |
| `user_id` | TEXT | FOREIGN KEY, ON DELETE CASCADE | Associated user profile |
| `encoding` | BLOB | NOT NULL | Pickled 128-d numpy array |

### 3. `attendance`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique log entry ID |
| `user_id` | TEXT | FOREIGN KEY, ON DELETE CASCADE | Logged user profile |
| `date` | TEXT | NOT NULL | Attendance date (YYYY-MM-DD) |
| `time` | TEXT | NOT NULL | Attendance time (HH:MM:SS) |
| `status` | TEXT | NOT NULL | Status indicator (Present) |
| *Constraint* | - | **UNIQUE(user_id, date)** | Restricts logs to one per user per day |

---

## 🚀 Windows Installation & Setup Guide

This project is fully compatible with Windows 10/11 running **Python 3.11** or **Python 3.12**.

### Prerequisites

1. **Python 3.11 / 3.12**: Make sure Python is installed and added to your system Environment variables (`PATH`).
2. **C++ Build Tools**: Because the `face_recognition` library compiles the C++ library `dlib` under the hood, you need Visual Studio C++ Build Tools installed on Windows. 
   * Download and install the [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
   * Select the **Desktop development with C++** workload during installation.

### Step-by-Step Installation

1. **Open PowerShell or Command Prompt** and navigate to the project directory:
   ```powershell
   cd C:\Users\hp\.gemini\antigravity\scratch\face_recognition_attendance
   ```

2. **Initialize a Virtual Environment**:
   ```powershell
   python -m venv .venv
   ```

3. **Activate the Virtual Environment**:
   * **PowerShell**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   * **Command Prompt**:
     ```cmd
     .venv\Scripts\activate.bat
     ```

4. **Install Dependencies**:
   Install all required python packages:
   ```powershell
   pip install -r requirements.txt
   ```
   *Note: If you run into SSL Certificate Verification errors on corporate networks, use the trusted host parameters:*
   ```powershell
   pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org
   ```

5. **Start the Flask Application**:
   ```powershell
   python app.py
   ```

6. **Access the System**:
   Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

---

## 💡 Troubleshooting

* **Webcam fails to open**: Close any other programs currently accessing your camera (Teams, Zoom, etc.). By default, the system accesses camera index `0`. If you use an external camera, modify the `camera_index` parameter in `app.py`.
* **dlib compilation fails**: Verify that **Visual Studio C++ Build Tools** is installed and CMake is configured. You can install cmake on Windows via pip (`pip install cmake`) which this project automatically handles.
