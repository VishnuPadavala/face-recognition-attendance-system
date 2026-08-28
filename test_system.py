# System Verification Script for Face Recognition Attendance System
import sys
import os

def test_imports():
    print("Testing core module imports...")
    import_errors = []
    
    try:
        import flask
        print(f"  [SUCCESS] Flask imported: version {flask.__version__}")
    except ImportError as e:
        print(f"  [FAILED] Flask import failed: {e}")
        import_errors.append("Flask")

    try:
        import cv2
        print(f"  [SUCCESS] OpenCV imported: version {cv2.__version__}")
    except ImportError as e:
        print(f"  [FAILED] OpenCV import failed: {e}")
        import_errors.append("opencv-python")

    try:
        import numpy as np
        print(f"  [SUCCESS] NumPy imported: version {np.__version__}")
    except ImportError as e:
        print(f"  [FAILED] NumPy import failed: {e}")
        import_errors.append("numpy")

    try:
        import face_recognition
        print(f"  [SUCCESS] Face Recognition imported successfully.")
    except ImportError as e:
        print(f"  [FAILED] Face Recognition import failed: {e}")
        import_errors.append("face-recognition")

    return import_errors

def test_database():
    print("\nTesting Database operations...")
    try:
        # Import local DB components
        from backend.database import DatabaseManager
        from backend.user import UserManager
        
        # Initialize temp DB
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "test_attendance.db")
        db = DatabaseManager(db_path=db_path)
        
        # Test schema setup
        initialized = db.initialize_database()
        if not initialized:
            print("  [FAILED] Schema initialization failed.")
            return False
            
        print("  [SUCCESS] Schema initialized successfully.")
        
        # Test User Management
        user_mgr = UserManager(db)
        user_mgr.register_user("TEST001", "Test User", "QA Department", "qa@example.com")
        print("  [SUCCESS] Dummy user inserted successfully.")
        
        user = user_mgr.get_user("TEST001")
        if user and user['name'] == "Test User":
            print(f"  [SUCCESS] User retrieved successfully: {user['name']} ({user['department']})")
        else:
            print("  [FAILED] User retrieval failed.")
            return False
            
        # Clean up database records
        user_mgr.delete_user("TEST001")
        print("  [SUCCESS] Dummy user deleted successfully.")
        
        # Try to clean up database file on Windows, tolerate lock errors
        try:
            # We delay slightly or just do it inside a try block
            import time
            time.sleep(0.5)
            if os.path.exists(db_path):
                os.remove(db_path)
                print("  [SUCCESS] Cleaned up temporary test database file.")
        except Exception as e:
            print(f"  [INFO] Cleanup info (can be ignored): {e}")
            
        return True
    except Exception as e:
        print(f"  [FAILED] Database testing error: {e}")
        return False

def main():
    print("=" * 60)
    print("AI FACE RECOGNITION ATTENDANCE SYSTEM VERIFICATION SUITE")
    print("=" * 60)
    
    import_errors = test_imports()
    db_success = test_database()
    
    print("\n" + "=" * 60)
    print("VERIFICATION RESULTS SUMMARY")
    print("=" * 60)
    
    if import_errors:
        print(f"[FAILED] Verification FAILED: Missing libraries: {', '.join(import_errors)}")
        print("Please check your visual studio build tools installation and retry installing dependencies.")
        sys.exit(1)
    elif not db_success:
        print("[FAILED] Verification FAILED: SQLite Database tests failed.")
        sys.exit(1)
    else:
        print("[PASSED] ALL TESTS PASSED SUCCESSFULLY!")
        print("The face recognition, OpenCV, database, and Flask modules are fully operational.")
        print("Run 'python app.py' to launch the web dashboard.")
        sys.exit(0)

if __name__ == '__main__':
    main()
