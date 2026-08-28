from flask import Flask, render_template, request, Response, redirect, url_for, jsonify, flash, send_file
import os
import cv2
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
from backend.camera import VideoCamera

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

@app.route('/api/register/capture_frame')
def api_register_capture_frame():
    """
    Triggered sequentially by the frontend. Grabs the webcam frame,
    verifies a single face is visible, generates encoding, and saves file.
    """
    user_id = request.args.get('user_id')
    index = request.args.get('index')
    
    if not user_id or not index:
        return jsonify({'success': False, 'message': 'Missing user_id or index'}), 400
        
    camera = VideoCamera.get_instance()
    if not camera:
        return jsonify({'success': False, 'message': 'Webcam is not initialized.'})
        
    frame = camera.get_frame()
    if frame is None:
        return jsonify({'success': False, 'message': 'Failed to grab frame from webcam.'})
        
    # Process image for face detection
    boxes = face_detector.detect_faces(frame)
    
    if len(boxes) == 0:
        return jsonify({'success': False, 'message': 'No face detected. Please center your face.'})
    if len(boxes) > 1:
        return jsonify({'success': False, 'message': 'Multiple faces detected. Please make sure only one person is in frame.'})
        
    # Get the bounding box of the face
    face_box = boxes[0]
    
    # Generate RGB image for face_recognition
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Extract encoding using dlib
    encodings = face_recognizer.get_face_encodings(rgb_frame, cv2_boxes=[face_box])
    
    if len(encodings) == 0:
        return jsonify({'success': False, 'message': 'Failed to extract face features. Try adjusting the lighting.'})
        
    encoding = encodings[0]
    
    try:
        # Save encoding to SQLite
        user_manager.add_face_encoding(user_id, encoding)
        
        # Save image to static folder
        user_faces_dir = os.path.join(app.root_path, "static", "faces", user_id)
        os.makedirs(user_faces_dir, exist_ok=True)
        
        # Save cropped or full frame? Full frame is preferred for backup references,
        # but let's draw a nice bounding box on a copy and save it for thumbnail visual confirmation!
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
        logger.error(f"Error during capture: {e}")
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

# ----------------- MJPEG Camera Streaming Generators -----------------

def gen_registration_stream(user_id):
    """
    Generator yielding webcam frames with a simple bounding box
    for user registration.
    """
    camera = VideoCamera()
    logger.info(f"Registration camera stream opened for user: {user_id}")
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue
                
            # Draw helper face bounds box
            boxes = face_detector.detect_faces(frame)
            for (x, y, w, h) in boxes:
                # Draw sleek indigo bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (241, 102, 99), 2)
                cv2.putText(frame, "Align Face", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (241, 102, 99), 1)

            # Encode as JPEG
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue
                
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
            time.sleep(0.04) # ~25 fps
    finally:
        camera.release()
        logger.info(f"Registration camera stream released for user: {user_id}")

def gen_attendance_stream():
    """
    Core attendance stream processing frames in real-time.
    Resizes images, runs recognition against cached database encodings,
    marks attendance, and overlays labels on frames.
    """
    camera = VideoCamera()
    logger.info("Attendance camera stream opened.")
    
    # Reload cached encodings from DB
    global known_encodings_cache
    update_encodings_cache()
    
    # Keep track of local scan states to avoid hitting DB lock or logging repeatedly in memory
    last_marked_cache = {}  # user_id -> timestamp of last match attempt

    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue
                
            # Create a copy for recognition to run on smaller dimensions (increases speed significantly!)
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            # Convert color space BGR -> RGB
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces on small frame
            small_boxes = face_detector.detect_faces(small_frame)
            
            if len(small_boxes) > 0:
                # Get encodings for detected faces using HOG
                encodings = face_recognizer.get_face_encodings(rgb_small_frame, cv2_boxes=small_boxes)
                
                for box, encoding in zip(small_boxes, encodings):
                    # Scale boxes back to original 100% size
                    sx, sy, sw, sh = box
                    x, y, w, h = sx * 4, sy * 4, sw * 4, sh * 4
                    
                    # Match query encoding against global in-memory DB cache
                    matched_user_id = face_recognizer.match_face(encoding, known_encodings_cache)
                    
                    if matched_user_id:
                        # Fetch user details
                        user_info = user_manager.get_user(matched_user_id)
                        name = user_info['name'] if user_info else matched_user_id
                        dept = user_info['department'] if user_info else ""
                        
                        # Mark attendance on background DB
                        now = datetime.now()
                        date_str = now.strftime('%Y-%m-%d')
                        time_str = now.strftime('%H:%M:%S')
                        
                        # Limit SQLite inserts to once per user per 5 seconds in memory to avoid log spam,
                        # database constraint will block double records on the daily level.
                        last_time = last_marked_cache.get(matched_user_id)
                        if last_time is None or (now - last_time).seconds > 10:
                            success, msg = attendance_manager.mark_attendance(matched_user_id, date_str, time_str)
                            last_marked_cache[matched_user_id] = now
                            
                        # Overlay Green Border + Name
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (129, 185, 16), 2)
                        
                        # Draw label box
                        cv2.rectangle(frame, (x, y + h - 35), (x + w, y + h), (129, 185, 16), cv2.FILLED)
                        cv2.putText(
                            frame, 
                            f"{name} ({dept})", 
                            (x + 6, y + h - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.5, 
                            (255, 255, 255), 
                            1, 
                            cv2.LINE_AA
                        )
                    else:
                        # Unknown Face
                        # Overlay Red Border + Unknown Person label
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (68, 68, 239), 2)
                        cv2.rectangle(frame, (x, y + h - 35), (x + w, y + h), (68, 68, 239), cv2.FILLED)
                        cv2.putText(
                            frame, 
                            "Unknown Person", 
                            (x + 6, y + h - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.55, 
                            (255, 255, 255), 
                            1, 
                            cv2.LINE_AA
                        )

            # Encode frame to JPEG
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue
                
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
            time.sleep(0.033)  # ~30 FPS
            
    finally:
        camera.release()
        logger.info("Attendance camera stream released.")

@app.route('/register_feed')
def register_feed():
    """
    Video streaming route for user registration.
    """
    user_id = request.args.get('user_id', '')
    return Response(gen_registration_stream(user_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/attendance_feed')
def attendance_feed():
    """
    Video streaming route for live attendance scanning.
    """
    return Response(gen_attendance_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ----------------- Application Entrypoint -----------------

if __name__ == '__main__':
    # Clean up any leftover camera instances in case of a crash or restart
    camera = VideoCamera.get_instance()
    if camera:
        camera.release()
        
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
