from datetime import datetime
import re
import uuid

class Complaint:
    """Complaint model class"""
    
    VALID_STATUSES = ['Pending', 'Under Review', 'Action Initiated', 'Resolved', 'Rejected']
    VALID_COMPLAINT_TYPES = ['air', 'water', 'land', 'noise', 'other']
    
    def __init__(self, full_name, email, phone, complaint_type, location, pincode, description, evidence_path=None):
        self.id = self.generate_complaint_id()
        self.full_name = self.validate_name(full_name)
        self.email = self.validate_email(email)
        self.phone = self.validate_phone(phone)
        self.complaint_type = self.validate_complaint_type(complaint_type)
        self.location = self.validate_location(location)
        self.pincode = self.validate_pincode(pincode)
        self.description = self.validate_description(description)
        self.evidence_path = evidence_path
        self.status = 'Pending'
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    @staticmethod
    def generate_complaint_id():
        """Generate unique complaint ID"""
        timestamp = int(datetime.now().timestamp() * 1000)
        unique_id = uuid.uuid4().hex[:6].upper()
        return f"MPCB{timestamp}{unique_id}"
    
    @staticmethod
    def validate_name(name):
        if not name or len(name.strip()) < 2:
            raise ValueError("Name must be at least 2 characters long")
        return name.strip()
    
    @staticmethod
    def validate_email(email):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email address")
        return email.lower()
    
    @staticmethod
    def validate_phone(phone):
        phone_pattern = r'^[6-9]\d{9}$'
        if not re.match(phone_pattern, phone):
            raise ValueError("Invalid phone number. Must be 10 digits starting with 6-9")
        return phone
    
    @staticmethod
    def validate_complaint_type(complaint_type):
        if complaint_type not in Complaint.VALID_COMPLAINT_TYPES:
            raise ValueError(f"Invalid complaint type. Must be one of: {Complaint.VALID_COMPLAINT_TYPES}")
        return complaint_type
    
    @staticmethod
    def validate_location(location):
        if not location or len(location.strip()) < 5:
            raise ValueError("Please provide a complete address")
        return location.strip()
    
    @staticmethod
    def validate_pincode(pincode):
        pincode_pattern = r'^\d{6}$'
        if not re.match(pincode_pattern, pincode):
            raise ValueError("Invalid pincode. Must be 6 digits")
        return pincode
    
    @staticmethod
    def validate_description(description):
        if not description or len(description.strip()) < 10:
            raise ValueError("Please provide a detailed description (minimum 10 characters)")
        if len(description) > 2000:
            raise ValueError("Description too long (maximum 2000 characters)")
        return description.strip()
    
    def to_dict(self):
        """Convert complaint to dictionary"""
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'complaint_type': self.complaint_type,
            'location': self.location,
            'pincode': self.pincode,
            'description': self.description,
            'evidence_path': self.evidence_path,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }