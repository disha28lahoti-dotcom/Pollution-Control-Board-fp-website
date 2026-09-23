import os
import json
import hashlib
import hmac
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from database import (
    init_database, get_db_connection, get_complaint_by_id,
    get_all_complaints, get_complaints_by_status, get_complaints_by_email,
    update_complaint_status, get_complaint_status_history,
    get_notifications, get_dashboard_stats
)
from models import Complaint

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'pdf'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    """Decorator for admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Initialize database on startup
init_database()

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/complaint')
def complaint_page():
    """Complaint filing page"""
    return render_template('complaint.html')

@app.route('/track')
def track_page():
    """Track complaint page"""
    return render_template('track.html')

@app.route('/awareness')
def awareness_page():
    """Awareness page"""
    return render_template('awareness.html')

# ==================== API ROUTES ====================

@app.route('/api/complaint', methods=['POST'])
def submit_complaint():
    """Submit a new complaint"""
    try:
        data = request.form
        file = request.files.get('evidence')
        
        # Handle file upload
        evidence_path = None
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            evidence_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(evidence_path)
        
        # Create complaint object
        complaint = Complaint(
            full_name=data.get('fullName'),
            email=data.get('email'),
            phone=data.get('phone'),
            complaint_type=data.get('complaintType'),
            location=data.get('location'),
            pincode=data.get('pincode'),
            description=data.get('description'),
            evidence_path=evidence_path
        )
        
        # Save to database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO complaints 
                (id, full_name, email, phone, complaint_type, location, pincode, description, evidence_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                complaint.id, complaint.full_name, complaint.email, complaint.phone,
                complaint.complaint_type, complaint.location, complaint.pincode,
                complaint.description, complaint.evidence_path, complaint.status
            ))
        
        return jsonify({
            'success': True,
            'message': 'Complaint submitted successfully',
            'complaint_id': complaint.id
        }), 201
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/complaint/<complaint_id>', methods=['GET'])
def get_complaint(complaint_id):
    """Get complaint by ID"""
    try:
        complaint = get_complaint_by_id(complaint_id)
        
        if not complaint:
            return jsonify({'error': 'Complaint not found'}), 404
        
        # Convert Row to dict
        complaint_dict = dict(complaint)
        
        # Get status history
        history = get_complaint_status_history(complaint_id)
        complaint_dict['status_history'] = [dict(h) for h in history]
        
        return jsonify({'success': True, 'complaint': complaint_dict})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/complaint/<complaint_id>/status', methods=['PUT'])
def update_status(complaint_id):
    """Update complaint status (admin only)"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        remarks = data.get('remarks')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        # Validate status
        if new_status not in ['Pending', 'Under Review', 'Action Initiated', 'Resolved', 'Rejected']:
            return jsonify({'error': 'Invalid status'}), 400
        
        # Update status
        success = update_complaint_status(complaint_id, new_status, remarks)
        
        if not success:
            return jsonify({'error': 'Complaint not found'}), 404
        
        return jsonify({'success': True, 'message': 'Status updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/complaint/<complaint_id>/history', methods=['GET'])
def get_history(complaint_id):
    """Get status history for a complaint"""
    try:
        history = get_complaint_status_history(complaint_id)
        return jsonify({'success': True, 'history': [dict(h) for h in history]})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/complaints', methods=['GET'])
def list_complaints():
    """List all complaints with filters (admin only)"""
    try:
        status = request.args.get('status')
        email = request.args.get('email')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        if email:
            complaints = get_complaints_by_email(email, limit)
        elif status:
            complaints = get_complaints_by_status(status, limit)
        else:
            complaints = get_all_complaints(limit, offset)
        
        return jsonify({
            'success': True,
            'complaints': [dict(c) for c in complaints],
            'count': len(complaints)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/complaint/track', methods=['POST'])
def track_complaint_api():
    """Track complaint by ID (POST for JSON request)"""
    try:
        data = request.get_json()
        complaint_id = data.get('complaint_id')
        
        if not complaint_id:
            return jsonify({'error': 'Complaint ID required'}), 400
        
        complaint = get_complaint_by_id(complaint_id)
        
        if not complaint:
            return jsonify({'error': 'Complaint not found'}), 404
        
        # Calculate status based on age (for demo purposes)
        # In production, this would come from the database status field
        complaint_dict = dict(complaint)
        
        # Calculate days since filing
        created_at = datetime.fromisoformat(complaint_dict['created_at'])
        days_diff = (datetime.now() - created_at).days
        
        # Determine status progression
        status_steps = {
            'step1': True,  # Submitted
            'step2': days_diff >= 1,  # Under Review
            'step3': days_diff >= 3,  # Action Initiated
            'step4': days_diff >= 5   # Resolved
        }
        
        complaint_dict['status_steps'] = status_steps
        complaint_dict['days_pending'] = days_diff
        
        return jsonify({'success': True, 'complaint': complaint_dict})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/<email>', methods=['GET'])
def get_user_notifications(email):
    """Get notifications for a user"""
    try:
        notifications = get_notifications(email=email)
        return jsonify({'success': True, 'notifications': [dict(n) for n in notifications]})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        stats = get_dashboard_stats()
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== ADMIN ROUTES ====================

@app.route('/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM admin_users WHERE username = ?', (username,))
            admin = cursor.fetchone()
        
        # Simple password check (use proper hashing in production)
        if admin and password == 'admin123':  # Replace with proper password hash check
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return jsonify({'success': True, 'message': 'Login successful'})
        
        return jsonify({'error': 'Invalid credentials'}), 401
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/admin/complaints', methods=['GET'])
@login_required
def admin_get_complaints():
    """Get all complaints for admin dashboard"""
    try:
        status = request.args.get('status')
        complaints = get_complaints_by_status(status) if status else get_all_complaints()
        return jsonify({'success': True, 'complaints': [dict(c) for c in complaints]})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/complaint/<complaint_id>', methods=['DELETE'])
@login_required
def admin_delete_complaint(complaint_id):
    """Delete a complaint (admin only)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM complaints WHERE id = ?', (complaint_id,))
            cursor.execute('DELETE FROM status_history WHERE complaint_id = ?', (complaint_id,))
            cursor.execute('DELETE FROM notifications WHERE complaint_id = ?', (complaint_id,))
        
        return jsonify({'success': True, 'message': 'Complaint deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== STATIC FILE SERVING ====================

@app.route('/style.css')
def serve_css():
    """Serve CSS file"""
    return app.send_static_file('style.css')

@app.route('/<path:filename>')
def serve_static_files(filename):
    """Serve static files"""
    if filename.endswith('.js'):
        return app.send_static_file(filename)
    return render_template(filename) if filename.endswith('.html') else ('File not found', 404)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)