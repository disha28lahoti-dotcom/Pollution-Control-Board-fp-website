import sqlite3
from contextlib import contextmanager

DATABASE_NAME = 'mpcb_grievance.db'

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    """Initialize database tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create complaints table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                complaint_type TEXT NOT NULL,
                location TEXT NOT NULL,
                pincode TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence_path TEXT,
                status TEXT DEFAULT 'Pending',
                status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create status_history table for tracking status changes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                remarks TEXT,
                changed_by TEXT DEFAULT 'System',
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (complaint_id) REFERENCES complaints(id)
            )
        ''')
        
        # Create admin_users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id TEXT,
                email TEXT,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (complaint_id) REFERENCES complaints(id)
            )
        ''')
        
        # Insert default admin (password: admin123 - hash this in production)
        cursor.execute('''
            INSERT OR IGNORE INTO admin_users (username, password_hash, role)
            VALUES ('admin', 'scrypt:32768:8:1$admin_salt$admin_hash', 'admin')
        ''')
        
        print("Database initialized successfully!")

def get_complaint_by_id(complaint_id):
    """Fetch a single complaint by ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,))
        return cursor.fetchone()

def get_all_complaints(limit=100, offset=0):
    """Fetch all complaints with pagination"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM complaints 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        return cursor.fetchall()

def get_complaints_by_status(status, limit=100):
    """Fetch complaints by status"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM complaints 
            WHERE status = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (status, limit))
        return cursor.fetchall()

def get_complaints_by_email(email, limit=50):
    """Fetch complaints by email"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM complaints 
            WHERE email = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (email, limit))
        return cursor.fetchall()

def update_complaint_status(complaint_id, new_status, remarks=None, changed_by='System'):
    """Update complaint status and log to history"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get current status
        cursor.execute('SELECT status FROM complaints WHERE id = ?', (complaint_id,))
        result = cursor.fetchone()
        if not result:
            return False
        
        old_status = result['status']
        
        # Update complaint status
        cursor.execute('''
            UPDATE complaints 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_status, complaint_id))
        
        # Log status change
        cursor.execute('''
            INSERT INTO status_history (complaint_id, old_status, new_status, remarks, changed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (complaint_id, old_status, new_status, remarks, changed_by))
        
        # Create notification
        cursor.execute('''
            INSERT INTO notifications (complaint_id, message)
            VALUES (?, ?)
        ''', (complaint_id, f'Your complaint status has been updated to: {new_status}'))
        
        return True

def get_complaint_status_history(complaint_id):
    """Get status history for a complaint"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM status_history 
            WHERE complaint_id = ? 
            ORDER BY changed_at DESC
        ''', (complaint_id,))
        return cursor.fetchall()

def get_notifications(email=None, complaint_id=None):
    """Get notifications for user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if email:
            cursor.execute('''
                SELECT n.*, c.email 
                FROM notifications n
                JOIN complaints c ON n.complaint_id = c.id
                WHERE c.email = ?
                ORDER BY created_at DESC
            ''', (email,))
        elif complaint_id:
            cursor.execute('''
                SELECT * FROM notifications 
                WHERE complaint_id = ? 
                ORDER BY created_at DESC
            ''', (complaint_id,))
        else:
            cursor.execute('SELECT * FROM notifications ORDER BY created_at DESC')
        return cursor.fetchall()

def get_dashboard_stats():
    """Get statistics for dashboard"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Total complaints
        cursor.execute('SELECT COUNT(*) as total FROM complaints')
        total = cursor.fetchone()['total']
        
        # Complaints by status
        cursor.execute('''
            SELECT status, COUNT(*) as count 
            FROM complaints 
            GROUP BY status
        ''')
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Recent complaints (last 7 days)
        cursor.execute('''
            SELECT COUNT(*) as recent 
            FROM complaints 
            WHERE created_at >= DATE('now', '-7 days')
        ''')
        recent = cursor.fetchone()['recent']
        
        # Average response time (in days)
        cursor.execute('''
            SELECT AVG(JULIANDAY(updated_at) - JULIANDAY(created_at)) as avg_days
            FROM complaints 
            WHERE status = 'Resolved'
        ''')
        avg_response = cursor.fetchone()['avg_days'] or 0
        
        return {
            'total_complaints': total,
            'pending': status_counts.get('Pending', 0),
            'under_review': status_counts.get('Under Review', 0),
            'action_initiated': status_counts.get('Action Initiated', 0),
            'resolved': status_counts.get('Resolved', 0),
            'recent_complaints': recent,
            'avg_response_days': round(avg_response, 1)
        }