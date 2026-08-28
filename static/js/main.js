// Dynamic Front-End JavaScript for Face Recognition Attendance System

document.addEventListener('DOMContentLoaded', () => {
    // Check if we are on the Attendance Camera Page
    if (document.getElementById('attendance-camera-page')) {
        initAttendancePage();
    }

    // Check if we are on the Register Page
    if (document.getElementById('register-page')) {
        initRegisterPage();
    }
});

/**
 * Attendance Page Initialization
 */
function initAttendancePage() {
    console.log("Attendance Page Loaded. Starting real-time logs polling...");
    
    // Poll recent logs immediately, then every 2 seconds
    fetchRecentLogs();
    const pollingInterval = setInterval(fetchRecentLogs, 2000);

    // Clean up interval when navigating away
    window.addEventListener('beforeunload', () => {
        clearInterval(pollingInterval);
    });
}

function fetchRecentLogs() {
    const tableBody = document.getElementById('recent-logs-tbody');
    if (!tableBody) return;

    fetch('/api/recent_attendance')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.records) {
                // Clear and rebuild table body
                tableBody.innerHTML = '';
                
                if (data.records.length === 0) {
                    tableBody.innerHTML = `
                        <tr>
                            <td colspan="5" style="text-align: center; color: var(--text-muted);">
                                No attendance marked today yet.
                            </td>
                        </tr>
                    `;
                    return;
                }

                data.records.forEach(r => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td><strong>${escapeHtml(r.user_id)}</strong></td>
                        <td>${escapeHtml(r.name)}</td>
                        <td>${escapeHtml(r.department)}</td>
                        <td>${escapeHtml(r.time)}</td>
                        <td><span class="badge badge-success">${escapeHtml(r.status)}</span></td>
                    `;
                    tableBody.appendChild(row);
                });
            }
        })
        .catch(err => console.error("Error fetching recent attendance:", err));
}

/**
 * Register Page Initialization
 */
function initRegisterPage() {
    console.log("Register Page Loaded.");
    
    const form = document.getElementById('register-form');
    const startBtn = document.getElementById('start-capture-btn');
    const captureSection = document.getElementById('capture-section');
    const formInputs = form.querySelectorAll('input, select');
    
    if (!form || !startBtn) return;

    startBtn.addEventListener('click', (e) => {
        e.preventDefault();
        
        // Form Validation
        const userId = document.getElementById('user_id').value.trim();
        const name = document.getElementById('name').value.trim();
        const department = document.getElementById('department').value.trim();
        const email = document.getElementById('email').value.trim();
        
        if (!userId || !name || !department) {
            showAlert('danger', 'Please fill in all required fields (User ID, Name, Department).');
            return;
        }

        // Disable form inputs to prevent modification during capture
        formInputs.forEach(input => input.disabled = true);
        startBtn.disabled = true;
        startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Initializing Camera...';

        // Initialize User on the backend
        fetch('/api/register/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, name: name, department: department, email: email })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show camera capture section
                captureSection.style.display = 'block';
                showAlert('success', 'User metadata saved. Initializing webcam capture. Look at the camera!');
                
                // Set up live registration video feed source
                const feedImg = document.getElementById('registration-feed');
                feedImg.src = `/register_feed?user_id=${encodeURIComponent(userId)}`;
                
                // Start capturing faces step-by-step
                captureFacesSequentially(userId);
            } else {
                showAlert('danger', data.message || 'Registration failed to initialize.');
                formInputs.forEach(input => input.disabled = false);
                startBtn.disabled = false;
                startBtn.innerHTML = '<i class="fas fa-camera"></i> Start Registration';
            }
        })
        .catch(err => {
            console.error(err);
            showAlert('danger', 'Connection error. Please try again.');
            formInputs.forEach(input => input.disabled = false);
            startBtn.disabled = false;
            startBtn.innerHTML = '<i class="fas fa-camera"></i> Start Registration';
        });
    });
}

function captureFacesSequentially(userId) {
    const progressBar = document.getElementById('registration-progress-bar');
    const progressLabel = document.getElementById('progress-label');
    const statusText = document.getElementById('capture-status-text');
    const gallery = document.getElementById('capture-gallery');
    
    let currentStep = 1;
    const totalSteps = 5;

    function captureNext() {
        if (currentStep > totalSteps) {
            // Completed registration
            statusText.innerText = "All face captures complete! Finalizing registration...";
            statusText.style.color = "var(--success-color)";
            
            setTimeout(() => {
                window.location.href = '/users?registered=true';
            }, 1500);
            return;
        }

        statusText.innerText = `Capturing Face Pose ${currentStep} of ${totalSteps}... Please hold still.`;
        statusText.style.color = "var(--text-primary)";

        // AJAX trigger to capture frame
        fetch(`/api/register/capture_frame?user_id=${encodeURIComponent(userId)}&index=${currentStep}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update progress bar
                    const percent = (currentStep / totalSteps) * 100;
                    progressBar.style.width = `${percent}%`;
                    progressLabel.innerText = `Progress: ${currentStep}/${totalSteps} captures`;
                    
                    // Add photo to gallery
                    const thumb = document.createElement('div');
                    thumb.className = 'gallery-thumbnail';
                    thumb.innerHTML = `
                        <img src="${data.image_path}?t=${new Date().getTime()}" alt="Face ${currentStep}">
                        <div class="overlay"><i class="fas fa-check"></i></div>
                    `;
                    gallery.appendChild(thumb);

                    currentStep++;
                    // Delay next capture slightly to allow user to adjust pose
                    setTimeout(captureNext, 1200);
                } else {
                    // Show error and retry this specific capture step
                    statusText.innerText = `Error: ${data.message}. Retrying pose ${currentStep}...`;
                    statusText.style.color = "var(--error-color)";
                    setTimeout(captureNext, 2000);
                }
            })
            .catch(err => {
                console.error(err);
                statusText.innerText = "Connection error. Retrying...";
                statusText.style.color = "var(--error-color)";
                setTimeout(captureNext, 2500);
            });
    }

    // Start the recursive capture chain after a short camera startup delay
    setTimeout(captureNext, 2000);
}

/**
 * Helpers
 */
function showAlert(type, message) {
    const alertBox = document.getElementById('page-alert');
    if (!alertBox) return;
    
    alertBox.className = `alert alert-${type}`;
    alertBox.innerHTML = message;
    alertBox.style.display = 'block';
    
    // Auto-scroll to alert
    alertBox.scrollIntoView({ behavior: 'smooth' });
}

function escapeHtml(str) {
    if (!str) return '';
    return str.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
