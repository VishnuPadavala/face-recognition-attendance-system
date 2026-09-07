from flask import Flask, render_template, request, Response, redirect, url_for, jsonify, flash, send_file
import os
import cv2
import base64
import time
import numpy as np
from datetime import datetime
import logging

# Import OOP components
from backend.database import DatabaseManager
from backend.user import UserManager
from backend.face_detection import FaceDetector
from backend.face_recognition import FaceRecognizer
from backend.attendance import AttendanceManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FlaskApplication")

app = Flask(__name__)
app.secret_key = "attendance_system_secret_key_for_flask_sessions"

# Initialize system components
db = DatabaseManager()
db.initialize_database()

user_manager = UserManager(db)
face_detector = FaceDetector()
face_recognizer = FaceRecognizer(tolerance=0.55)  # Slightly stricter tolerance for accurate recognition
attendance_manager = AttendanceManager(db)

# Global variables/cache
known_encodings_cache = {}
last_marked_cache = {}  # user_id -> datetime of last attendance mark (cooldown)

def update_encodings_cache():
    """
    Loads all registered face encodings from SQLite into memory for fast real-time comparison.
    """
    global known_encodings_cache
    known_encodings_cache = user_manager.get_all_encodings()
    logger.info(f"Refreshed face encodings cache. Loaded users: {list(known_encodings_cache.keys())}")

# Load encodings cache on startup
update_encodings_cache()

# Ensure faces directory exists
os.makedirs(os.path.join(app.root_path, "static", "faces"), exist_ok=True)

# ----------------- Flask UI Routes -----------------

@app.route('/')
def dashboard():
    """
    Main overview page showing daily attendance logs and metrics.
    """
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Query daily metrics
    users = user_manager.get_all_users()
    total_users = len(users)
    
    recent_records = attendance_manager.get_attendance_records(date_filter=today_str)
    present_today = len(recent_records)
    
    attendance_rate = 0
    if total_users > 0:
        attendance_rate = round((present_today / total_users) * 100)
    
    stats = {
        'total_users': total_users,
        'present_today': present_today,
        'attendance_rate': attendance_rate
    }
    
    return render_template(
        'dashboard.html', 
        stats=stats, 
        recent_records=recent_records[:5],  # Limit dashboard to last 5 logs
        active_page='dashboard'
    )

@app.route('/register')
def register():
    """
    Registration form and camera capture page.
    """
    return render_template('register.html', active_page='register')

@app.route('/attendance_cam')
def attendance_cam():
    """
    Real-time face recognition scanner screen.
    """
    return render_template('attendance_cam.html', active_page='attendance_cam')

@app.route('/users')
def users():
    """
    Page listing all registered user profiles.
    """
    # Fetch registered parameter to show a success message
    registered = request.args.get('registered')
    if registered:
        flash("User registration and face enrollment successful!", "success")
        
    all_users = user_manager.get_all_users()
    return render_template('users.html', users=all_users, active_page='users')

@app.route('/users/delete/<user_id>', methods=['POST'])
def delete_user_route(user_id):
    """
    Endpoint to delete a registered user.
    """
    try:
        user_manager.delete_user(user_id)
        update_encodings_cache()
        flash(f"User {user_id} deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete user {user_id}: {e}", "danger")
    return redirect(url_for('users'))

@app.route('/records')
def records():
    """
    Logs history table with date filters.
    """
    date_filter = request.args.get('date_filter')
    
    # Defaults to today's logs if no filter is supplied on first load
    # (But let user see all records if they reset filters)
    records_list = attendance_manager.get_attendance_records(date_filter=date_filter)
    
    return render_template(
        'records.html', 
        records=records_list, 
        date_filter=date_filter, 
        active_page='records'
    )

@app.route('/download_csv')
def download_csv():
    """
    Exports filtered logs to CSV and triggers browser download.
    """
    date_filter = request.args.get('date_filter')
    
    # Build clean filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"attendance_report_{timestamp}.csv"
    if date_filter:
        filename = f"attendance_report_{date_filter}.csv"
        
    temp_csv_path = os.path.join(app.root_path, "database", filename)
    
    # Export records
    success, filepath = attendance_manager.export_attendance_to_csv(temp_csv_path, date_filter=date_filter)
    
    if success:
        try:
            # Send file for download and delete it locally after sending
            response = send_file(filepath, as_attachment=True, download_name=filename)
            # Remove the temporary file after request lifecycle (accomplished by a helper thread or clean up)
            @response.call_on_close
            def cleanup():
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"Cleaned up temporary export CSV: {filepath}")
            return response
        except Exception as e:
            logger.error(f"Error sending CSV file: {e}")
            flash("Error exporting report.", "danger")
            return redirect(url_for('records'))
    else:
        flash(f"Export failed: {filepath}", "danger")
        return redirect(url_for('records'))

# ----------------- Async API Routes -----------------

@app.route('/api/register/init', methods=['POST'])
def api_register_init():
    """
    Saves text metadata for a new user in the DB.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
        
    user_id = data.get('user_id')
    name = data.get('name')
    department = data.get('department')
    email = data.get('email')
    
    # Check duplicate user ID
    if user_manager.get_user(user_id) is not None:
        return jsonify({'success': False, 'message': f'User ID "{user_id}" is already registered.'})
        
    try:
        user_manager.register_user(user_id, name, department, email)
        return jsonify({'success': True, 'message': 'User details initialized.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/register/capture_frame_upload', methods=['POST'])
def api_register_capture_frame_upload():
    """
    Accepts a base64-encoded JPEG frame from the browser webcam (WebRTC).
    Verifies a single face is visible, generates encoding, and saves file.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    user_id = data.get('user_id')
    index = data.get('index')
    image_data = data.get('image')

    if not user_id or index is None or not image_data:
        return jsonify({'success': False, 'message': 'Missing user_id, index, or image'}), 400

    # Decode base64 image from browser
    frame = decode_base64_image(image_data)
    if frame is None:
        return jsonify({'success': False, 'message': 'Invalid image data received.'}), 400

    # Process image for face detection
    boxes = face_detector.detect_faces(frame)

    if len(boxes) == 0:
        return jsonify({'success': False, 'message': 'No face detected. Please center your face.'})
    if len(boxes) > 1:
        return jsonify({'success': False, 'message': 'Multiple faces detected. Please make sure only one person is in frame.'})

    face_box = boxes[0]

    # Generate RGB image for face_recognition library
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Extract encoding using dlib
    encodings = face_recognizer.get_face_encodings(rgb_frame, cv2_boxes=[face_box])

    if len(encodings) == 0:
        return jsonify({'success': False, 'message': 'Failed to extract face features. Try adjusting the lighting.'})

    encoding = encodings[0]

    try:
        # Save encoding to SQLite
        user_manager.add_face_encoding(user_id, encoding)

        # Save image file to static folder for thumbnail display
        user_faces_dir = os.path.join(app.root_path, "static", "faces", user_id)
        os.makedirs(user_faces_dir, exist_ok=True)

        img_name = f"img_{index}.jpg"
        img_path = os.path.join(user_faces_dir, img_name)
        cv2.imwrite(img_path, frame)

        # Refresh global encodings cache after the final photo capture
        if int(index) == 5:
            update_encodings_cache()

        return jsonify({
            'success': True,
            'message': f'Capture {index}/5 complete.',
            'image_path': f'/static/faces/{user_id}/{img_name}'
        })
    except Exception as e:
        logger.error(f"Error during capture upload: {e}")
        return jsonify({'success': False, 'message': f'Save failed: {e}'})

@app.route('/api/recent_attendance')
def api_recent_attendance():
    """
    Returns today's attendance logs for live updates polling.
    """
    today_str = datetime.now().strftime('%Y-%m-%d')
    records_list = attendance_manager.get_attendance_records(date_filter=today_str)
    
    serialized_records = []
    for r in records_list:
        serialized_records.append({
            'user_id': r['user_id'],
            'name': r['name'],
            'department': r['department'],
            'time': r['time'],
            'status': r['status']
        })
        
    return jsonify({'success': True, 'records': serialized_records})


# ----------------- Helper Functions -----------------

def decode_base64_image(data_url):
    """
    Decodes a base64-encoded image data URL (from browser canvas/WebRTC)
    into an OpenCV BGR numpy array.
    """
    try:
        # Strip the data URL prefix (e.g. "data:image/jpeg;base64,")
        if ',' in data_url:
            data_url = data_url.split(',')[1]
        img_bytes = base64.b64decode(data_url)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        logger.error(f"Failed to decode base64 image: {e}")
        return None


# ----------------- Browser-Based Face Recognition API -----------------

@app.route('/api/recognize_frame', methods=['POST'])
def api_recognize_frame():
    """
    Accepts a base64-encoded JPEG frame from the user's browser webcam (WebRTC/Canvas).
    Runs face detection + recognition and returns matched face details as JSON.
    The browser overlays bounding boxes and names on a canvas element.
    """
    global last_marked_cache

    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'success': False, 'message': 'No image provided'}), 400

    frame = decode_base64_image(data['image'])
    if frame is None:
        return jsonify({'success': False, 'message': 'Invalid image data'}), 400

    # Scale down for faster processing (same as original streaming pipeline)
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Detect faces on the smaller frame
    small_boxes = face_detector.detect_faces(small_frame)

    faces = []
    if len(small_boxes) > 0:
        encodings = face_recognizer.get_face_encodings(rgb_small_frame, cv2_boxes=small_boxes)

        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M:%S')

        for box, encoding in zip(small_boxes, encodings):
            # Scale bounding box back to original frame size
            sx, sy, sw, sh = box
            x, y, w, h = int(sx * 4), int(sy * 4), int(sw * 4), int(sh * 4)

            matched_user_id = face_recognizer.match_face(encoding, known_encodings_cache)

            if matched_user_id:
                user_info = user_manager.get_user(matched_user_id)
                name = user_info['name'] if user_info else matched_user_id
                dept = user_info['department'] if user_info else ''

                # Cooldown: only mark attendance once per user per 10 seconds
                last_time = last_marked_cache.get(matched_user_id)
                if last_time is None or (now - last_time).seconds > 10:
                    attendance_manager.mark_attendance(matched_user_id, date_str, time_str)
                    last_marked_cache[matched_user_id] = now

                faces.append({
                    'matched': True,
                    'user_id': matched_user_id,
                    'name': name,
                    'department': dept,
                    'box': [x, y, w, h]
                })
            else:
                faces.append({
                    'matched': False,
                    'name': 'Unknown',
                    'department': '',
                    'box': [x, y, w, h]
                })

    return jsonify({'success': True, 'faces': faces})



# ----------------- Application Entrypoint -----------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
