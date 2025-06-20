# --- START OF FILE models.py ---

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, UTC
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association Model for a Many-to-Many relationship between Program and Course.
# This is the correct place for the 'semester' information.
class ProgramCourse(db.Model):
    __tablename__ = 'program_courses'
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), primary_key=True)
    semester = db.Column(db.Integer, nullable=False)

    # Relationships to Program and Course
    program = db.relationship('Program', back_populates='program_courses_association')
    course = db.relationship('Course', back_populates='program_courses_association')

    def __repr__(self):
        return f'<ProgramCourse(program_id={self.program_id}, course_id={self.course_id}, semester={self.semester})>'

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='student')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    phone = db.Column(db.String(20))
    nationality = db.Column(db.String(50))
    education = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    military_status = db.Column(db.String(20))
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    applications = db.relationship('Application', back_populates='user', lazy=True)
    documents = db.relationship('Document', back_populates='user', lazy=True)
    certificates = db.relationship('Certificate', back_populates='user', lazy=True)
    tickets = db.relationship('Ticket', back_populates='user', lazy=True)
    notifications = db.relationship('Notification', back_populates='user', lazy=True)
    enrollments = db.relationship('CourseEnrollment', back_populates='student', lazy=True)
    payments = db.relationship('Payment', back_populates='user', lazy=True)
    projects = db.relationship('Project', back_populates='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    def is_admin(self):
        return self.role == 'admin'

class Program(db.Model):
    __tablename__ = 'programs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    degree_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    arabic_name = db.Column(db.String(200))
    arabic_description = db.Column(db.Text)
    type = db.Column(db.String(50), default='Professional')
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    applications = db.relationship('Application', back_populates='program_relation', lazy=True)
    # Corrected: Added viewonly=True to prevent conflict
    courses = db.relationship('Course', secondary='program_courses', back_populates='programs', viewonly=True)
    program_courses_association = db.relationship('ProgramCourse', back_populates='program', cascade='all, delete-orphan')

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    credits = db.Column(db.Integer, default=3, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    # Corrected: Added viewonly=True to prevent conflict
    programs = db.relationship('Program', secondary='program_courses', back_populates='courses', viewonly=True)
    enrollments = db.relationship('CourseEnrollment', back_populates='course', lazy=True)
    program_courses_association = db.relationship('ProgramCourse', back_populates='course', cascade='all, delete-orphan')

# ... (rest of the models.py file is unchanged) ...
class Application(db.Model):
    __tablename__ = 'application'
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    program = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default='Pending Review')
    payment_status = db.Column(db.String(50), default='Pending Payment')
    date_submitted = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    academic_year = db.Column(db.String(20))
    semester = db.Column(db.String(10))
    program_type = db.Column(db.String(50))

    user = db.relationship('User', back_populates='applications')
    program_relation = db.relationship('Program', back_populates='applications')
    documents = db.relationship('Document', back_populates='application', lazy=True)
    student_id = db.relationship('StudentID', back_populates='application', uselist=False, lazy=True)
    payment = db.relationship('Payment', backref='application', uselist=False)

class Document(db.Model):
    __tablename__ = 'document'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'))
    name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default='Uploaded')
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    
    user = db.relationship('User', back_populates='documents')
    application = db.relationship('Application', back_populates='documents')

class CourseEnrollment(db.Model):
    __tablename__ = 'course_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    grade = db.Column(db.String(5))
    grade_numeric = db.Column(db.Float)
    gpa_value = db.Column(db.Float)
    status = db.Column(db.String(20), default='Enrolled')
    enrollment_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    academic_year = db.Column(db.String(20))
    semester = db.Column(db.String(50))

    student = db.relationship('User', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')

class StudentID(db.Model):
    __tablename__ = 'student_id'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), unique=True, nullable=False)
    issue_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    application = db.relationship('Application', back_populates='student_id')

class Certificate(db.Model):
    __tablename__ = 'certificates'
    id = db.Column(db.Integer, primary_key=True)
    cert_id = db.Column(db.String(50), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.Text)
    copies = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default='Pending Payment')
    request_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    user = db.relationship('User', back_populates='certificates')

class Ticket(db.Model):
    __tablename__ = 'ticket'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Open')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    user = db.relationship('User', back_populates='tickets')
    messages = db.relationship('TicketMessage', back_populates='ticket', lazy=True, order_by='TicketMessage.created_at', cascade="all, delete-orphan")

class TicketMessage(db.Model):
    __tablename__ = 'ticket_message'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    sender = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    ticket = db.relationship('Ticket', back_populates='messages')

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    url = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', back_populates='notifications')

class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'))
    certificate_id = db.Column(db.Integer, db.ForeignKey('certificates.id'))
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Completed')
    transaction_id = db.Column(db.String(100))
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    user = db.relationship('User', back_populates='payments')

class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    url = db.Column(db.String(200))
    image_path = db.Column(db.String(200))
    is_popular = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='projects')

class News(db.Model):
    __tablename__ = 'news' 
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    image_path = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))