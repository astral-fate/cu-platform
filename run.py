
import os
import json
import sys
import traceback
import logging
import time
from datetime import datetime, UTC, date
import click
from functools import wraps
import base64
# --- New Imports for Email Verification ---
from itsdangerous import URLSafeTimedSerializer
# --- New Mailtrap Import ---
try:
    import mailtrap as mt
    MAILTRAP_AVAILABLE = True
except ImportError:
    MAILTRAP_AVAILABLE = False
    # TRANSLATED
    print("تحذير: مكتبة Mailtrap غير مثبتة. سيتم تعطيل إرسال البريد الإلكتروني. قم بتشغيل 'pip install mailtrap' لتفعيلها.")


# --- Third-Party Libraries ---
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, session,
    send_from_directory, current_app
)
from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired
import requests  # For calling Gemini API
from sqlalchemy import text
from sqlalchemy.orm import joinedload, selectinload  # Add selectinload
from markupsafe import Markup, escape

# --- Conditional Import for PDF Processing ---
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    # TRANSLATED
    print("تحذير: مكتبة PyMuPDF (fitz) غير مثبتة. سيتم تعطيل استخراج النص من ملفات PDF.")

# --- Application Models ---
from models import (
    db, User, Application, Document, Certificate,
    Payment, Project, News, Course, CourseEnrollment,
    Ticket, TicketMessage, Notification, StudentID, Program, ProgramCourse
)

# Configure logging for better debugging
logging.basicConfig(
    level=logging.INFO, # Changed to INFO for production, DEBUG is very verbose
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Define the form class before it's used
class NewApplicationForm(FlaskForm):
    # TRANSLATED choices
    degree_type = SelectField('نوع الدرجة', validators=[DataRequired()],
                            choices=[('Diploma', 'دبلوم'), ('Master', 'ماجستير'), ('PhD', 'دكتوراه')])
    program = SelectField('البرنامج', validators=[DataRequired()], choices=[])  # Initialize with empty list
    academic_year = SelectField('العام الدراسي', validators=[DataRequired()], choices=[])  # Initialize with empty list
    # TRANSLATED choices
    semester = SelectField('الفصل الدراسي', validators=[DataRequired()],
                         choices=[('1', 'الفصل الدراسي الأول'), ('2', 'الفصل الدراسي الثاني')])
    # TRANSLATED label
    submit = SubmitField('تقديم الطلب النهائي')

# Initialize Flask app
app = Flask(__name__)

### VERCEL FIX: Use /tmp for uploads
UPLOAD_DIR = os.path.join('/tmp', 'uploads')

# Configure app with proper paths
app.config.update(
    SECRET_KEY='your-secret-key-goes-here', # Keep secret key as is
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL'),
    
    UPLOAD_FOLDER=UPLOAD_DIR,
    # --- New Mail Configurations for Mailtrap ---
    MAILTRAP_API_TOKEN=os.environ.get('MAILTRAP_API_TOKEN'),
    ### FINAL DOMAIN FIX: Use the new custom domain for the sender email ###
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@cu-platform.com')
)

# Ensure the /tmp/uploads directory exists at runtime.
with app.app_context():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- New: Serializer for generating secure tokens ---
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Initialize extensions
csrf = CSRFProtect(app)
db.init_app(app)
migrate = Migrate(app, db)



# Create database tables if they don't exist


with app.app_context():
    db.create_all()

    # --- ADD THIS BLOCK TO CHECK AND POPULATE THE DATABASE ON STARTUP ---
    try:
        # Check if the database has any programs. This is a lightweight check.
        program_count = db.session.query(Program.id).count()
        app.logger.info(f"Checking for programs in the database. Found: {program_count}")

        # If there are no programs, run the population script.
        if program_count == 0:
            app.logger.info("Database is empty. Running population script...")
            from populate_db import populate_database
            populate_database()
            app.logger.info("Database population script finished.")
        else:
            app.logger.info("Database already populated. Skipping script.")

    except Exception as e:
        app.logger.error(f"An error occurred during the database population check: {e}", exc_info=True)
    # --- END OF THE NEW BLOCK ---


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
# TRANSLATED: Default message if user tries to access protected page without login
login_manager.login_message = "الرجاء تسجيل الدخول للوصول إلى هذه الصفحة."
login_manager.login_message_category = "info" # Or 'warning'
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- MODIFIED: Email sending helper function using Mailtrap ---
def send_email(to_email, subject, body):
    """Helper function to send email using the Mailtrap API."""
    if not MAILTRAP_AVAILABLE:
        app.logger.error("Mailtrap library not installed. Cannot send email.")
        return

    token = app.config.get('MAILTRAP_API_TOKEN')
    if not token:
        app.logger.error("MAILTRAP_API_TOKEN is not configured in environment variables. Cannot send email.")
        return

    sender_email = app.config.get('MAIL_DEFAULT_SENDER')
    sender_name = "CU Graduate Studies Platform"

    app.logger.info(f"Preparing to send email to {to_email} via Mailtrap from {sender_email}")

    mail = mt.Mail(
        sender=mt.Address(email=sender_email, name=sender_name),
        to=[mt.Address(email=to_email)],
        subject=subject,
        html=body,
        category="System Notifications",
    )

    client = mt.MailtrapClient(token=token)

    try:
        response = client.send(mail)
        app.logger.info(f"Email sent successfully to {to_email} via Mailtrap. Response: {response}")
    except Exception as e:
        app.logger.error(f"Failed to send email to {to_email} using Mailtrap. Error: {e}")

### VERCEL FIX: Route to serve files from /tmp
@app.route('/uploads/<path:filename>')
@login_required 
def serve_upload(filename):
    """Serve a file from the UPLOAD_FOLDER (/tmp/uploads)."""
    if not current_user.is_admin():
        # Security check: only allow users to access their own documents
        doc = Document.query.filter_by(file_path=f"uploads/{filename}", user_id=current_user.id).first()
        if not doc:
            app.logger.warning(f"User {current_user.id} attempted to access unauthorized file: {filename}")
            flash('الوصول مرفوض', 'danger')
            return redirect(url_for('student_dashboard'))
            
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.template_filter('time_ago')
def time_ago_filter(time):
    """Format a timestamp as 'time ago' (e.g., "3 hours ago")"""
    now = datetime.now(UTC)

    # Make the input time timezone-aware if it's naive
    if time.tzinfo is None:
        time = time.replace(tzinfo=UTC)

    diff = now - time
    seconds = diff.total_seconds()

    # TRANSLATED: Time difference strings
    if seconds < 60:
        return "الآن"
    elif seconds < 3600:  # Less than an hour
        minutes = int(seconds / 60)
        if minutes == 1:
            return "منذ دقيقة واحدة"
        elif minutes == 2:
            return "منذ دقيقتين"
        elif 3 <= minutes <= 10:
            return f"منذ {minutes} دقائق"
        else:
            return f"منذ {minutes} دقيقة"
    elif seconds < 86400: # Less than a day
        hours = int(seconds / 3600)
        if hours == 1:
            return "منذ ساعة واحدة"
        elif hours == 2:
            return "منذ ساعتين"
        elif 3 <= hours <= 10:
            return f"منذ {hours} ساعات"
        else:
            return f"منذ {hours} ساعة"
    elif seconds < 604800: # Less than a week
        days = int(seconds / 86400)
        if days == 1:
            return "منذ يوم واحد"
        elif days == 2:
            return "منذ يومين"
        elif 3 <= days <= 10:
            return f"منذ {days} أيام"
        else:
            return f"منذ {days} يومًا"
    elif seconds < 2592000: # Less than a month
        weeks = int(seconds / 604800)
        if weeks == 1:
            return "منذ أسبوع واحد"
        elif weeks == 2:
            return "منذ أسبوعين"
        elif 3 <= weeks <= 10:
            return f"منذ {weeks} أسابيع"
        else:
            return f"منذ {weeks} أسبوعًا"
    else:
        # Fallback to date format if longer than a month
        return time.strftime("%Y-%m-%d")


@app.template_filter('initials')
def initials_filter(name):
    if not name:
        return "UN" # Keep initials logic as is

    parts = name.split()
    if len(parts) == 1:
        return parts[0][0].upper()
    else:
        return (parts[0][0] + parts[-1][0]).upper()


@app.template_filter('slice')
def slice_filter(iterable, start, end=None):
    if end is None:
        return iterable[start:]
    return iterable[start:end]


@app.template_filter('format_date')
def format_date_filter(date):
    if date is None:
        return ""
    try:
        # Can adjust format if needed for Arabic preferences, e.g., "%d %b %Y"
        return date.strftime("%b %d, %Y")
    except:
        return str(date)

# Add a template filter to convert newlines to <br> tags
@app.template_filter('nl2br')
def nl2br_filter(text):
    if not text:
        return ""
    return Markup(escape(text).replace('\n', '<br>\n'))

@app.route('/')
def index():
    # Get only active and featured projects for the homepage
    featured_projects = Project.query.filter_by(
        is_active=True,
        is_popular=True
    ).order_by(
        Project.created_at.desc()
    ).limit(3).all()

    # Fetch news items (tagged as 'news')
    news_items = News.query.filter_by(type='news', is_active=True)\
        .order_by(News.date.desc()).limit(3).all()

    # Fetch announcements (tagged as 'announcement')
    announcements = News.query.filter_by(type='announcement', is_active=True)\
        .order_by(News.date.desc()).limit(4).all()

    return render_template('index.html',
                          featured_projects=featured_projects,
                          news_items=news_items,
                          announcements=announcements)

# MODIFIED: login() function to check for verification status
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))

    class LoginForm(FlaskForm):
        pass  # Empty form just for CSRF protection

    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        # Check user existence and password first
        if user and user.check_password(password):
            # --- New Verification Check ---
            # Admins can log in without verification, students cannot.
            if not user.is_verified and not user.is_admin():
                # TRANSLATED
                flash('يجب عليك تفعيل حسابك قبل تسجيل الدخول. يرجى مراجعة بريدك الإلكتروني للحصول على رابط التفعيل.', 'warning')
                return render_template('login.html', form=form)

            # If password is correct and user is verified (or is an admin)
            login_user(user)
            return redirect(url_for('admin_dashboard' if user.is_admin() else 'student_dashboard'))
        else:
            # General error for wrong email/password
            # TRANSLATED
            flash('البريد الإلكتروني أو كلمة المرور غير صالحة', 'danger')

    return render_template('login.html', form=form)

    # Add this new route to manually create admin user
@app.route('/create-admin', methods=['GET'])
def create_admin():
    # Check if admin user exists
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            email='admin@example.com',
            full_name='Admin User', # Keep 'Admin User' or translate? Let's keep for clarity
            role='admin',
            is_verified=True # Admins are auto-verified
        )
        admin.set_password('adminpassword') # Keep password as is
        db.session.add(admin)
        db.session.commit()
        # TRANSLATED
        return 'تم إنشاء المستخدم المسؤول بنجاح!'
    else:
        # Reset admin password and ensure they are verified
        admin.set_password('adminpassword') # Keep password as is
        admin.is_verified = True
        db.session.commit()
        # TRANSLATED
        return 'تمت إعادة تعيين كلمة مرور المستخدم المسؤول إلى "adminpassword"'

# MODIFIED: register() function to send verification email
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('student_dashboard'))

    class RegisterForm(FlaskForm):
        pass  # Empty form just for CSRF protection

    form = RegisterForm()
    if request.method == 'POST' and form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')
        full_name = request.form.get('fullName')
        phone = request.form.get('phone')
        nationality = request.form.get('nationality')
        education = request.form.get('education')

        if password != confirm_password:
            # TRANSLATED
            flash('كلمتا المرور غير متطابقتين', 'danger')
            return render_template('register.html', form=form)

        if User.query.filter_by(email=email).first():
            # TRANSLATED
            flash('البريد الإلكتروني مسجل بالفعل', 'danger')
            return render_template('register.html', form=form)

        # Create user but set as unverified
        user = User(
            email=email,
            full_name=full_name,
            phone=phone,
            nationality=nationality,
            education=education,
            is_verified=False  # New users are not verified by default
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # --- Email Verification Logic ---
        try:
            # Generate a time-sensitive token
            token = s.dumps(user.email, salt='email-confirm')
            
            # Create the verification URL.
            verification_url = url_for('verify_email', token=token, _external=True)

            # Prepare email content (HTML)
            # TRANSLATED email body
            email_subject = 'تفعيل حسابك في مشروع جامعة القاهرة'
            email_body_html = f"""
            <html dir="rtl" lang="ar">
            <head><meta charset="UTF-8"></head>
            <body>
                <p>مرحباً {user.full_name},</p>
                <p>شكراً لتسجيلك في بوابة الدراسات العليا. يرجى الضغط على الرابط التالي لتفعيل حسابك:</p>
                <p style="text-align: center;">
                    <a href="{verification_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        تفعيل الحساب
                    </a>
                </p>
                <p>إذا لم يعمل الزر، يمكنك نسخ ولصق الرابط التالي في متصفحك:</p>
                <p>{verification_url}</p>
                <p>إذا لم تقم بطلب هذا التسجيل، يرجى تجاهل هذا البريد الإلكتروني.</p>
                <hr>
                <p>شكراً لك،</p>
                <p>فريق مشروع جامعة القاهرة</p>
            </body>
            </html>
            """

            # Send the email using the helper function
            send_email(user.email, email_subject, email_body_html)

            # Flash a success message to the user
            # TRANSLATED flash message
            flash('تم التسجيل بنجاح! تم إرسال رابط تفعيل إلى بريدك الإلكتروني. يرجى التحقق من بريدك لتفعيل حسابك.', 'info')

        except Exception as e:
            app.logger.error(f"Error sending verification email for {user.email}: {e}", exc_info=True)
            # TRANSLATED flash message for when email fails to send
            flash('تم تسجيل حسابك، ولكن حدث خطأ أثناء إرسال بريد التفعيل. يرجى الاتصال بالدعم.', 'warning')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# --- New Route for Email Verification ---
@app.route('/verify-email/<token>')
def verify_email(token):
    try:
        # Verify the token, max_age is in seconds (e.g., 1 day = 86400 seconds)
        email = s.loads(token, salt='email-confirm', max_age=86400)
    except Exception as e:
        app.logger.warning(f"Email verification failed. Token: {token}, Error: {e}")
        # TRANSLATED
        flash('رابط التفعيل غير صالح أو انتهت صلاحيته.', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first()

    if not user:
        # TRANSLATED
        flash('المستخدم غير موجود.', 'danger')
        return redirect(url_for('login'))

    if user.is_verified:
        # TRANSLATED
        flash('تم تفعيل هذا الحساب بالفعل. يمكنك تسجيل الدخول.', 'info')
    else:
        user.is_verified = True
        db.session.commit()
        # TRANSLATED
        flash('تم تفعيل حسابك بنجاح! يمكنك الآن تسجيل الدخول.', 'success')

    return redirect(url_for('login'))


@app.route('/programs')
def programs():
    return render_template('programs.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/admin/applications')
@login_required

def admin_applications():
    applications = Application.query.all()
    return render_template('admin/applications.html', applications=applications)

@app.route('/admin/application/<int:application_id>/<action>', methods=['POST'])
@login_required
def admin_application_action(application_id, action):
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'}), 403

    try:
        application = Application.query.options(joinedload(Application.user)).get_or_404(application_id)
        student = application.user
        original_status = application.status
        new_status = original_status
        action_arabic = ""

        if action == 'approve':
            # TRANSLATED status
            new_status = 'مقبول مبدئياً'
            action_arabic = 'الموافقة على'
        elif action == 'reject':
            # TRANSLATED status
            new_status = 'المستندات مرفوضة'
            action_arabic = 'رفض'
        else:
            # TRANSLATED
            return jsonify({'success': False, 'message': 'إجراء غير صالح'}), 400

        # Only proceed if status is changing
        if new_status != original_status:
            application.status = new_status
            # Create notification for student
            # TRANSLATED notification message
            notification = Notification(
                user_id=application.user_id,
                message=f'تم تحديث حالة طلبك رقم {application.app_id} إلى: {application.status}',
                url=url_for('student_applications')
            )
            db.session.add(notification)
            db.session.commit()

            # --- NOTIFICATION & EMAIL ---
            # Send an email to the student about the status update
            email_subject = f"تحديث بخصوص طلب التقديم رقم {application.app_id}"
            email_body_html = f"""
            <html dir="rtl" lang="ar">
            <head><meta charset="UTF-8"></head>
            <body>
                <p>مرحباً {student.full_name},</p>
                <p>تم تحديث حالة طلب التقديم الخاص بك لبرنامج "{application.program}" إلى: <strong>{application.status}</strong>.</p>
                {'<p>يمكنك الآن المتابعة لدفع الرسوم الدراسية من خلال لوحة التحكم الخاصة بك.</p>' if action == 'approve' else ''}
                <p>للاطلاع على كافة تفاصيل طلباتك، يرجى زيارة لوحة التحكم الخاصة بك.</p>
                <p style="text-align: center;">
                    <a href="{url_for('student_dashboard', _external=True)}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        الانتقال إلى لوحة التحكم
                    </a>
                </p>
                <hr>
                <p>فريق الدراسات العليا</p>
            </body>
            </html>
            """
            send_email(student.email, email_subject, email_body_html)

        message = f'تم تغيير حالة الطلب إلى {new_status}'
        return jsonify({
            'success': True,
            'message': message,
            'new_status': new_status
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in admin_application_action: {e}", exc_info=True)
        # TRANSLATED part of the message
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'}), 500

# Add the missing route for sending notes
@app.route('/admin/application/send-note', methods=['POST'])
@login_required
def admin_send_note():
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'}), 403

    try:
        data = request.get_json()
        application_id = data.get('application_id')
        subject = data.get('subject')
        message_text = data.get('message')

        if not application_id or not subject or not message_text:
            # TRANSLATED
            return jsonify({'success': False, 'message': 'البيانات المطلوبة غير مكتملة'}), 400

        application = Application.query.get_or_404(application_id)
        student = application.user

        # Generate a unique ticket ID
        ticket_count = Ticket.query.count() + 1
        ticket_id_str = f"NOTE-{ticket_count:03d}"

        # Create a new ticket to represent the note
        new_ticket = Ticket(
            ticket_id=ticket_id_str,
            user_id=student.id,
            subject=subject,
            # TRANSLATED status
            status='مفتوحة'
        )
        db.session.add(new_ticket)
        db.session.flush()

        # Add the message from the admin
        admin_message = TicketMessage(
            ticket_id=new_ticket.id,
            sender='Admin',
            message=message_text,
            created_at=datetime.now(UTC)
        )
        db.session.add(admin_message)

        # Create notification for the student
        # TRANSLATED notification message
        notification = Notification(
            user_id=student.id,
            message=f'ملاحظة جديدة بخصوص طلبك {application.app_id}: {subject}',
            url=url_for('student_ticket_detail', ticket_id=new_ticket.id)
        )
        db.session.add(notification)
        db.session.commit()

        # --- NOTIFICATION & EMAIL ---
        # Send an email to the student about the new note/message
        email_subject = f"ملاحظة من الإدارة بخصوص طلبك: {subject}"
        email_body_html = f"""
        <html dir="rtl" lang="ar">
        <head><meta charset="UTF-8"></head>
        <body>
            <p>مرحباً {student.full_name},</p>
            <p>لديك رسالة جديدة من الإدارة بخصوص طلب التقديم رقم {application.app_id}.</p>
            <p><strong>الموضوع:</strong> {subject}</p>
            <p>لعرض الرسالة والرد عليها، يرجى زيارة قسم الدعم الفني في حسابك.</p>
            <p style="text-align: center;">
                <a href="{url_for('student_ticket_detail', ticket_id=new_ticket.id, _external=True)}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    عرض الرسالة
                </a>
            </p>
            <hr>
            <p>فريق الدراسات العليا</p>
        </body>
        </html>
        """
        send_email(student.email, email_subject, email_body_html)
        # TRANSLATED
        return jsonify({'success': True, 'message': 'تم إرسال الملاحظة بنجاح'})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error sending note: {str(e)}", exc_info=True)
        # TRANSLATED
        return jsonify({'success': False, 'message': f'خطأ في إرسال الملاحظة: {str(e)}'}), 500


@app.route('/admin/enrollments')
@login_required
def admin_enrollments():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    # Get applications with paid status that need student IDs
    # TRANSLATED statuses
    enrollments = db.session.query(Application).filter_by(
        status='مقبول مبدئياً', # Changed from 'Documents Approved'
        payment_status='مدفوع'
    ).outerjoin(
        StudentID,
        Application.id == StudentID.application_id
    ).filter(
        StudentID.id == None
    ).all()

    # Get applications with student IDs
    enrolled_students = db.session.query(Application, StudentID).join(
        StudentID,
        Application.id == StudentID.application_id
    ).all()

    return render_template('admin/enrollments.html',
                          enrollments=enrollments,
                          enrolled_students=enrolled_students)

@app.route('/admin/generate_student_id/<int:app_id>', methods=['POST'])
@login_required
def generate_student_id(app_id):
    start_time = time.time()
    current_app.logger.info(f"Generating ID for app_id {app_id} - START")

    # Eager load the program_relation to get the English name and the user
    application = Application.query.options(
        joinedload(Application.user),
        joinedload(Application.program_relation)
    ).get_or_404(app_id)
    student = application.user

    # Get custom prefix from request body
    request_data = request.get_json() or {}
    custom_prefix_part = request_data.get('prefix', '').strip().upper()

    # --- Start Building the ID ---
    year_part = str(datetime.now(UTC).year)

    # Determine the prefix part (custom or default)
    if custom_prefix_part:
        prefix_part = custom_prefix_part
    else:
        is_international = student.nationality != 'Egyptian'
        prefix_part = 'INT' if is_international else 'NAT'

    # Determine the program code part from the English name
    program_english_name = ""
    if application.program_relation and application.program_relation.name:
        program_english_name = application.program_relation.name
    else:
        # Fallback to the display name if the relation fails (not ideal)
        program_english_name = application.program

    program_code_part = ''.join(word[0].upper() for word in program_english_name.split())
    if not program_code_part:
        program_code_part = "GEN" # Generic code if name is empty

    # --- Find the next sequential number ---
    # Construct the prefix for the DB query (e.g., "2024-NAT-SE-")
    prefix_for_query = f"{year_part}-{prefix_part}-{program_code_part}-"
    latest_student = StudentID.query.filter(
        StudentID.student_id.like(f'{prefix_for_query}%')
    ).order_by(StudentID.student_id.desc()).first()

    if latest_student:
        try:
            last_number = int(latest_student.student_id.split('-')[-1])
            new_number_part = f"{last_number + 1:04d}"
        except (ValueError, IndexError):
            # Fallback if the last part is not a number
            new_number_part = "0001"
    else:
        new_number_part = "0001"

    # Assemble the final ID string
    new_student_id_str = f"{prefix_for_query}{new_number_part}"
    
    new_id_entry = StudentID(application_id=app_id, student_id=new_student_id_str)
    db.session.add(new_id_entry)

    # Create notification for student
    # TRANSLATED notification
    notification = Notification(
        user_id=application.user_id,
        message=f'تم إنشاء رقم الطالب الخاص بك: {new_student_id_str}',
        url=url_for('student_profile')
    )
    db.session.add(notification)

    # Update application status
    # TRANSLATED status
    application.status = 'مسجل' # Enrolled

    db.session.commit()

    # --- NOTIFICATION & EMAIL ---
    # Send an email to the student with their new ID
    email_subject = "تم إنشاء رقم الطالب الجامعي الخاص بك"
    email_body_html = f"""
    <html dir="rtl" lang="ar">
    <head><meta charset="UTF-8"></head>
    <body>
        <p>مرحباً {student.full_name},</p>
        <p>تهانينا! تم تسجيلك بنجاح في برنامج "{application.program}" وقد تم إنشاء رقم الطالب الجامعي الخاص بك.</p>
        <p>رقمك الجامعي هو: <strong>{new_student_id_str}</strong></p>
        <p>يرجى الاحتفاظ بهذا الرقم حيث ستحتاج إليه في جميع معاملاتك الأكاديمية.</p>
        <p style="text-align: center;">
            <a href="{url_for('student_profile', _external=True)}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                عرض ملفك الشخصي
            </a>
        </p>
        <hr>
        <p>فريق الدراسات العليا</p>
    </body>
    </html>
    """
    send_email(student.email, email_subject, email_body_html)

    end_time = time.time()
    current_app.logger.info(f"Generating ID for app_id {app_id} - END | Total time: {end_time - start_time:.4f}s")
    # TRANSLATED success message
    return jsonify(success=True, student_id=new_student_id_str, message="تم إنشاء رقم الطالب بنجاح.")




@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin():
        # TRANSLATED
        flash('الوصول مرفوض: صلاحيات المسؤول مطلوبة', 'danger')
        return redirect(url_for('student_dashboard'))

    # Get stats for dashboard
    # TRANSLATED statuses
    applications_count = Application.query.filter_by(status='قيد المراجعة').count()
    payment_pending_count = Application.query.filter_by(status='مقبول مبدئياً', payment_status='بانتظار الدفع').count()
    certificate_requests = Certificate.query.count()
    open_tickets = Ticket.query.filter_by(status='مفتوحة').count()

    # Get recent applications and tickets
    recent_applications = Application.query.order_by(Application.date_submitted.desc()).limit(3).all()
    recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(3).all()

    # Get recent certificate requests
    recent_certificates = Certificate.query.order_by(Certificate.request_date.desc()).limit(3).all()

    # --- New: Student statistics ---
    from sqlalchemy import func

    # Total students with student IDs (enrolled)
    total_students = (
        db.session.query(func.count(StudentID.id))
        .join(Application, StudentID.application_id == Application.id)
        .join(User, Application.user_id == User.id)
        .filter(User.role == 'student')
        .scalar()
    )

    # National students (Egyptian)
    national_students = (
        db.session.query(func.count(StudentID.id))
        .join(Application, StudentID.application_id == Application.id)
        .join(User, Application.user_id == User.id)
        .filter(User.role == 'student', func.lower(User.nationality) == 'egyptian')
        .scalar()
    )
    # International students = total - national
    international_students = total_students - national_students if total_students is not None and national_students is not None else 0

    # Top 3 registered courses (by enrollment count)
    top_courses = (
        db.session.query(Course.title, func.count(CourseEnrollment.id).label('enroll_count'))
        .join(CourseEnrollment, Course.id == CourseEnrollment.course_id)
        .group_by(Course.id)
        .order_by(func.count(CourseEnrollment.id).desc())
        .limit(3)
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        applications_count=applications_count,
        payment_pending_count=payment_pending_count,
        certificate_requests=certificate_requests,
        open_tickets=open_tickets,
        recent_applications=recent_applications,
        recent_tickets=recent_tickets,
        recent_certificates=recent_certificates,
        # New stats:
        total_students=total_students,
        national_students=national_students,
        international_students=international_students,
        top_courses=top_courses
    )


# end of dashbord routes
@app.route('/admin/certificates/update/<int:cert_id>', methods=['POST'])
@login_required
def admin_update_certificate(cert_id):
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'})

    try:
        certificate = Certificate.query.options(joinedload(Certificate.user)).get_or_404(cert_id)
        student = certificate.user
        
        # Update certificate status
        # TRANSLATED status
        certificate.status = 'جاهزة للاستلام' # Ready for Pickup

        # Create notification for student
        # TRANSLATED notification
        notification = Notification(
            user_id=certificate.user_id,
            message=f'شهادتك رقم {certificate.cert_id} جاهزة للاستلام.',
            url=url_for('student_certificates')
        )

        db.session.add(notification)
        db.session.commit()

        # --- NOTIFICATION & EMAIL ---
        # Send an email to the student
        email_subject = f"شهادتك رقم {certificate.cert_id} جاهزة للاستلام"
        email_body_html = f"""
        <html dir="rtl" lang="ar">
        <head><meta charset="UTF-8"></head>
        <body>
            <p>مرحباً {student.full_name},</p>
            <p>يسعدنا إعلامك بأن طلب الشهادة الخاص بك (النوع: {certificate.type}) أصبح جاهزًا للاستلام.</p>
            <p>يمكنك التوجه إلى مكتب شؤون الطلاب لاستلامها خلال ساعات العمل الرسمية.</p>
            <p style="text-align: center;">
                <a href="{url_for('student_certificates', _external=True)}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    عرض طلبات الشهادات
                </a>
            </p>
            <hr>
            <p>فريق الدراسات العليا</p>
        </body>
        </html>
        """
        send_email(student.email, email_subject, email_body_html)

        # TRANSLATED success message
        return jsonify({
            'success': True,
            'cert_id': certificate.cert_id,
            'message': 'تم تحديد الشهادة كـ جاهزة للاستلام'
        })

    except Exception as e:
        db.session.rollback()
        # TRANSLATED part of message
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@app.route('/admin/certificates')
@login_required
def admin_certificates():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    # Get all certificates including pending payment ones
    certificates = Certificate.query.order_by(Certificate.request_date.desc()).all()

    return render_template('admin/certificates.html', certificates=certificates)


@app.route('/admin/tickets')
@login_required
def admin_tickets():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
    return render_template('admin/tickets.html', tickets=tickets)

@app.route('/admin/tickets/<int:ticket_id>')
@login_required
def admin_ticket_detail(ticket_id):
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template('admin/ticket_detail.html', ticket=ticket)

@app.route('/admin/tickets/reply/<int:ticket_id>', methods=['POST'])
@login_required
def admin_ticket_reply(ticket_id):
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'})

    try:
        ticket = Ticket.query.options(joinedload(Ticket.user)).get_or_404(ticket_id)
        student = ticket.user
        message_text = request.form.get('message')

        if not message_text:
            # TRANSLATED
            return jsonify({'success': False, 'message': 'لا يمكن أن تكون الرسالة فارغة'})

        # Create a new message
        new_message = TicketMessage(
            ticket_id=ticket.id,
            sender='Admin',
            message=message_text,
            created_at=datetime.now(UTC)
        )

        # Update ticket status to In Progress if it's Open
        # TRANSLATED statuses
        if ticket.status == 'مفتوحة':
            ticket.status = 'قيد المعالجة' # In Progress

        # Create notification for student
        # TRANSLATED notification message
        notification = Notification(
            user_id=ticket.user_id,
            message=f'رد جديد على تذكرتك: {ticket.subject}',
            url=url_for('student_ticket_detail', ticket_id=ticket.id)
        )

        db.session.add(new_message)
        db.session.add(notification)
        db.session.commit()

        # --- NOTIFICATION & EMAIL ---
        # Send an email to the student about the reply
        email_subject = f"رد جديد على تذكرتك: {ticket.subject}"
        email_body_html = f"""
        <html dir="rtl" lang="ar">
        <head><meta charset="UTF-8"></head>
        <body>
            <p>مرحباً {student.full_name},</p>
            <p>لقد تلقيت رداً جديداً على تذكرة الدعم الخاصة بك بخصوص "{ticket.subject}".</p>
            <p>لعرض الرد والمتابعة، يرجى الضغط على الرابط أدناه.</p>
            <p style="text-align: center;">
                <a href="{url_for('student_ticket_detail', ticket_id=ticket.id, _external=True)}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    عرض التذكرة
                </a>
            </p>
            <hr>
            <p>فريق الدعم الفني</p>
        </body>
        </html>
        """
        send_email(student.email, email_subject, email_body_html)

        # TRANSLATED success message
        return jsonify({
            'success': True,
            'message': 'تم إرسال الرد بنجاح',
            'data': {
                'message': message_text,
                'created_at': new_message.created_at.strftime('%Y-%m-%d %H:%M'),
                'sender': 'Admin'
            }
        })

    except Exception as e:
        db.session.rollback()
        # TRANSLATED part of message
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'})

@app.route('/admin/tickets/update_status/<int:ticket_id>', methods=['POST'])
@login_required
def admin_update_ticket_status(ticket_id):
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'})

    ticket = Ticket.query.get_or_404(ticket_id)
    new_status = request.form.get('status')

    # TRANSLATED statuses for check and notification
    valid_statuses = ['مفتوحة', 'قيد المعالجة', 'مغلقة'] # Open, In Progress, Closed
    status_map = {
        'Open': 'مفتوحة',
        'In Progress': 'قيد المعالجة',
        'Closed': 'مغلقة'
    }
    new_status_arabic = status_map.get(new_status, new_status) # Get Arabic or keep original if not found

    if new_status_arabic in valid_statuses:
        ticket.status = new_status_arabic

        # Notify student of status change
        # TRANSLATED notification message
        notification = Notification(
            user_id=ticket.user_id,
            message=f'تم تحديث حالة تذكرتك {ticket.ticket_id} إلى {new_status_arabic}.',
            url=url_for('student_ticket_detail', ticket_id=ticket.id)
        )
        db.session.add(notification)
        db.session.commit()

        return jsonify({'success': True})
    # TRANSLATED error message
    return jsonify({'success': False, 'message': 'حالة غير صالحة'})

@app.route('/admin/settings')
@login_required
def admin_settings():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    # In a real app, you might load settings from a database
    # Keep keys in English for code, translate labels in the template
    settings = {
        'local_fee': 600,
        'international_fee': 1500,
        'certificate_fee': 200,
        'email_notifications': True,
        'sms_notifications': True,
        'push_notifications': False
    }

    return render_template('admin/settings.html', settings=settings)



# Student Routes
def calculate_gpa(user_id):
    """Calculate cumulative GPA for a student based on their course grades"""
    try:
        # Try to query with the new column
        # TRANSLATED status
        enrollments = CourseEnrollment.query.filter(
            CourseEnrollment.student_id == user_id,
            CourseEnrollment.status == 'مكتمل' # Completed
            ).all()

        if not enrollments:
            return None

        total_gpa_points = 0
        total_credits = 0

        for enrollment in enrollments:
            # Skip courses without grades or in progress (Using translated status)
            if not enrollment.grade or enrollment.status != 'مكتمل':
                continue

            # Get course credits using Session.get instead of Query.get
            course = db.session.get(Course, enrollment.course_id)
            if not course:
                continue

            # GPA value mapping (Keep grades as keys, potentially add Arabic equivalent in comments)
            gpa_map = {
                'A+': 4.0, 'A': 4.0, 'A-': 3.7, # ممتاز مرتفع / ممتاز
                'B+': 3.3, 'B': 3.0, 'B-': 2.7, # جيد جداً
                'C+': 2.3, 'C': 2.0, 'C-': 1.7, # جيد
                'D+': 1.3, 'D': 1.0,             # مقبول
                'F': 0.0                         # راسب
            }

            # Use the existing gpa_value if available, otherwise calculate from grade
            gpa_value = 0.0 # Initialize gpa_value
            try:
                # Check if the enrollment object has the gpa_value attribute
                if hasattr(enrollment, 'gpa_value') and enrollment.gpa_value is not None:
                    gpa_value = enrollment.gpa_value
                else:
                    # Fallback to calculating from grade if gpa_value is missing or None
                    gpa_value = gpa_map.get(enrollment.grade, 0.0)
            except AttributeError:
                # Handle cases where the gpa_value column might not exist yet
                app.logger.warning(f"Enrollment ID {enrollment.id} missing gpa_value attribute. Calculating from grade.")
                gpa_value = gpa_map.get(enrollment.grade, 0.0)

            # Add to total GPA calculation
            total_gpa_points += gpa_value * course.credits
            total_credits += course.credits

        # Return None if no completed courses with grades
        if total_credits == 0:
            return None

        # Calculate and return GPA, handle division by zero
        cumulative_gpa = round(total_gpa_points / total_credits, 2) if total_credits > 0 else 0.0
        return cumulative_gpa

    except Exception as e:
        app.logger.error(f"Error calculating GPA for user {user_id}: {str(e)}", exc_info=True)
        # Return None in case of error
        return None

def get_current_academic_year():
    today = date.today()
    # Simple logic: If before August 1st, it's part of the previous academic year start
    if today.month < 8:
        return f"{today.year - 1}-{today.year}"
    else:
        return f"{today.year}-{today.year + 1}"

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    applications = Application.query.filter_by(user_id=current_user.id).all()
    documents = Document.query.filter_by(user_id=current_user.id).all()
    certificates = Certificate.query.filter_by(user_id=current_user.id).all()
    tickets = Ticket.query.filter_by(user_id=current_user.id).all()

    # Get unread notifications
    notifications = Notification.query.filter_by(user_id=current_user.id, read=False).order_by(Notification.created_at.desc()).all()

    # Check if there are any applications with approved documents that need payment
    # TRANSLATED statuses
    payment_required = any(app.status == 'مقبول مبدئياً' and app.payment_status == 'بانتظار الدفع' for app in applications)

    # Check if there are any certificates ready for pickup
    # TRANSLATED status
    certificate_ready = any(cert.status == 'جاهزة للاستلام' for cert in certificates)

    # Get student ID and program info
    student_id_obj = StudentID.query.join(Application).filter(
        Application.user_id == current_user.id
    ).first()

    student_id = student_id_obj.student_id if student_id_obj else None
    program = student_id_obj.application.program if student_id_obj else None

    # Calculate cumulative GPA
    cumulative_gpa = calculate_gpa(current_user.id)

    # Calculate total credits (for the dashboard)
    total_credits = 0
    try:
        # Use raw SQL to avoid ORM querying columns that might not exist yet
        # TRANSLATED status
        sql_query = text("SELECT ce.course_id FROM course_enrollments ce WHERE ce.student_id = :student_id AND ce.status = :status")
        result = db.session.execute(sql_query, {"student_id": current_user.id, "status": "مكتمل"}) # 'Completed'
        course_ids = [row[0] for row in result]

        # Now get the credits for each course
        for course_id in course_ids:
            course = db.session.get(Course, course_id)
            if course:
                total_credits += course.credits
    except Exception as e:
        print(f"Error calculating credits: {str(e)}")

    return render_template(
        'student/dashboard.html',
        applications=applications,
        documents=documents,
        certificates=certificates,
        tickets=tickets,
        notifications=notifications,
        payment_required=payment_required,
        certificate_ready=certificate_ready,
        student_id=student_id,
        program=program,
        cumulative_gpa=cumulative_gpa,
        total_credits=total_credits
    )

@app.route('/student/applications')
@login_required
def student_applications():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    applications = Application.query.filter_by(user_id=current_user.id).all()
    return render_template('student/applications.html', applications=applications)

@app.route('/student/new_application', methods=['GET', 'POST'])
@login_required
def student_new_application():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    form = NewApplicationForm()

    # Initialize academic_year choices for the current and next 2 years
    current_year = datetime.now(UTC).year
    academic_years = [(f"{year}/{year+1}", f"{year}/{year+1}") for year in range(current_year, current_year + 3)]
    form.academic_year.choices = academic_years

    if request.method == 'POST':
        app.logger.info("--- New Application POST Request Received ---")

        degree_type = request.form.get('degree_type')
        program_json = request.form.get('program')
        academic_year = request.form.get('academic_year')
        semester = request.form.get('semester')

        # Get document files
        document_files = request.files.getlist('document_files[]')
        document_types = request.form.getlist('document_types[]')

        app.logger.info(f"Received degree_type: '{degree_type}'")
        app.logger.info(f"Received program_json: '{program_json}'")
        app.logger.info(f"Received academic_year: '{academic_year}'")
        app.logger.info(f"Received semester: '{semester}'")
        app.logger.info(f"Received {len(document_files)} document files and {len(document_types)} document types")

        # Check if any program field is None or empty
        if not all([degree_type, program_json, academic_year, semester]):
            # TRANSLATED flash message
            flash('جميع حقول البرنامج مطلوبة', 'danger')

            # Repopulate choices for form display
            if degree_type:
                try:
                    programs = Program.query.filter_by(degree_type=degree_type).order_by(Program.name).all()
                    # Display Arabic name if available
                    program_choices = [(json.dumps({'id': p.id, 'name': p.name, 'degree_type': p.degree_type, 'arabic_name': p.arabic_name}), f"{p.arabic_name if p.arabic_name else p.name}") for p in programs]
                    form.program.choices = program_choices
                except Exception as e:
                    app.logger.error(f"Error repopulating program choices: {str(e)}")
                    form.program.choices = []
            else:
                form.program.choices = []

            return render_template('student/new_application.html', form=form, now=datetime.now(UTC))

        # Check if documents are provided
        if len(document_files) == 0 or len(document_types) == 0 or len(document_files) != len(document_types):
            # TRANSLATED flash message
            flash('المستندات المطلوبة غير مكتملة أو غير متطابقة', 'danger') # Added "or mismatched"
            return render_template('student/new_application.html', form=form, now=datetime.now(UTC))

        # Populate form choices for validation
        try:
            # Set program choices with the submitted program
            if program_json:
                try:
                    program_data = json.loads(program_json)
                    # Use Arabic name for display if available
                    display_name = program_data.get('arabic_name', program_data.get('name', 'Unknown'))
                    form.program.choices = [(program_json, display_name)]
                except json.JSONDecodeError:
                    form.program.choices = []
                    app.logger.warning(f"Invalid program JSON: {program_json}")
            else:
                form.program.choices = []

            # Make sure academic year choices are populated
            if not form.academic_year.choices:
                form.academic_year.choices = academic_years
        except Exception as e:
            app.logger.error(f"Error setting form choices: {str(e)}", exc_info=True)
            form.program.choices = []

        # Validate the form (uses choices set above)
        if form.validate_on_submit():
            app.logger.info("Form validation passed.")
            try:
                # Begin a database transaction
                db.session.begin_nested()  # Create a savepoint

                # Process the application data
                program_info = json.loads(program_json)
                program_id = program_info.get('id')
                program_db = db.session.get(Program, program_id) if program_id else None
                # TRANSLATED program type default
                program_type = program_db.type if program_db and hasattr(program_db, 'type') else 'مهني' # Professional

                # Build program display name (prioritize Arabic)
                program_name_display = program_info.get('name', '') # English name as fallback
                arabic_name = program_info.get('arabic_name')
                degree_type_arabic = dict(form.degree_type.choices).get(degree_type, degree_type) # Get Arabic degree name

                if arabic_name:
                    program_name_display = arabic_name
                else:
                    # Fallback display if no Arabic name
                    program_name_display = f"{degree_type_arabic} - {program_name_display}"

                # Create unique application ID
                app_count = Application.query.count() + 1
                app_id = f"APP-{datetime.now(UTC).strftime('%Y%m%d')}-{app_count:04d}" # Keep format

                # Create application record
                application = Application(
                    app_id=app_id,
                    user_id=current_user.id,
                    program=program_name_display, # Use the Arabic name if available
                    program_id=program_id,
                    # TRANSLATED status
                    status='قيد المراجعة', # Pending Review
                    date_submitted=datetime.now(UTC),
                    academic_year=academic_year,
                    semester=semester,
                    program_type=program_type # Store program type
                )

                db.session.add(application)
                db.session.flush()  # Get application ID without committing

                # Process document uploads
                for i, file in enumerate(document_files):
                    if file and file.filename:
                        # Use the submitted document type directly (should be Arabic from the form)
                        doc_type = document_types[i] if i < len(document_types) else "مستند غير معروف" # unknown

                        # Create a unique filename
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
                        new_filename = f"{current_user.id}_{timestamp}_{i}_{filename}"

                        # Save file
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                        file.save(file_path)

                        # Create document record
                        document = Document(
                            user_id=current_user.id,
                            application_id=application.id,
                            name=doc_type,  # Use document type as name (already Arabic)
                            file_path=f"uploads/{new_filename}", # Keep path structure
                            # TRANSLATED status
                            status='تم الرفع', # Uploaded
                            uploaded_at=datetime.now(UTC)
                        )

                        db.session.add(document)

                # --- NEW: Create Notification for student ---
                # TRANSLATED notification message
                notification = Notification(
                    user_id=current_user.id,
                    message=f'تم استلام طلبك رقم {application.app_id} بنجاح. وهو الآن قيد المراجعة.',
                    url=url_for('student_applications')
                )
                db.session.add(notification)

                # Commit all changes (application, documents, notification)
                db.session.commit()

                # --- NEW: Send Confirmation Email ---
                try:
                    email_subject = f"تأكيد استلام طلب التقديم رقم: {application.app_id}"
                    email_body_html = f"""
                    <html dir="rtl" lang="ar">
                    <head><meta charset="UTF-8"></head>
                    <body>
                        <p>مرحباً {current_user.full_name},</p>
                        <p>لقد استلمنا بنجاح طلب التقديم الخاص بك لبرنامج "{application.program}".</p>
                        <p>رقم طلبك هو: <strong>{application.app_id}</strong></p>
                        <p>حالة الطلب الحالية هي "<strong>قيد المراجعة</strong>". سنقوم بمراجعة طلبك ومستنداتك وسنخطرك بأي تحديثات.</p>
                        <p>يمكنك متابعة حالة طلبك في أي وقت من خلال لوحة التحكم الخاصة بك.</p>
                        <p style="text-align: center;">
                            <a href="{url_for('student_applications', _external=True)}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                                عرض طلباتي
                            </a>
                        </p>
                        <hr>
                        <p>شكراً لك،</p>
                        <p>فريق القبول والتسجيل</p>
                    </body>
                    </html>
                    """
                    send_email(current_user.email, email_subject, email_body_html)
                    app.logger.info(f"Confirmation email sent for application {application.app_id} to {current_user.email}")
                except Exception as email_exc:
                    app.logger.error(f"Failed to send confirmation email for application {application.app_id}: {email_exc}", exc_info=True)
                    # Don't fail the request, just log it. The application is already submitted.


                app.logger.info(f"Application {app_id} with {len(document_files)} documents submitted successfully for user {current_user.id}")
                # TRANSLATED and UPDATED flash message
                flash('تم تقديم طلبك بنجاح! تم إرسال تأكيد إلى بريدك الإلكتروني.', 'success')
                return redirect(url_for('student_applications'))

            except json.JSONDecodeError:
                app.logger.error("JSONDecodeError processing program data.", exc_info=True)
                # TRANSLATED flash message
                flash('خطأ في بيانات البرنامج المختار. يرجى إعادة المحاولة.', 'danger')
                db.session.rollback()
                # Repopulate form choices on error
                if degree_type:
                    try:
                        programs = Program.query.filter_by(degree_type=degree_type).order_by(Program.name).all()
                        program_choices = [(json.dumps({'id': p.id, 'name': p.name, 'degree_type': p.degree_type, 'arabic_name': p.arabic_name}), f"{p.arabic_name if p.arabic_name else p.name}") for p in programs]
                        form.program.choices = program_choices
                    except Exception: pass
                return render_template('student/new_application.html', form=form, now=datetime.now(UTC))

            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error submitting application: {str(e)}", exc_info=True)
                # TRANSLATED flash message
                flash('حدث خطأ أثناء تقديم الطلب. الرجاء المحاولة مرة أخرى.', 'danger')
                # Repopulate form choices on error
                if degree_type:
                    try:
                        programs = Program.query.filter_by(degree_type=degree_type).order_by(Program.name).all()
                        program_choices = [(json.dumps({'id': p.id, 'name': p.name, 'degree_type': p.degree_type, 'arabic_name': p.arabic_name}), f"{p.arabic_name if p.arabic_name else p.name}") for p in programs]
                        form.program.choices = program_choices
                    except Exception: pass
                return render_template('student/new_application.html', form=form, now=datetime.now(UTC))
        else:
            app.logger.warning(f"Form validation failed. Errors: {form.errors}")
            # TRANSLATED flash message
            flash('هناك أخطاء في النموذج. يرجى التحقق من الحقول.', 'danger')
            # Repopulate form choices on validation failure
            if degree_type:
                 try:
                     programs = Program.query.filter_by(degree_type=degree_type).order_by(Program.name).all()
                     program_choices = [(json.dumps({'id': p.id, 'name': p.name, 'degree_type': p.degree_type, 'arabic_name': p.arabic_name}), f"{p.arabic_name if p.arabic_name else p.name}") for p in programs]
                     form.program.choices = program_choices
                 except Exception: pass
            return render_template('student/new_application.html', form=form, now=datetime.now(UTC))

    # GET request handling
    # Ensure choices are populated for the initial GET request too
    # This part might be better handled with AJAX based on degree selection,
    # but for now, we'll leave it empty initially.
    form.program.choices = [] # Start with empty program choices
    return render_template('student/new_application.html', form=form, now=datetime.now(UTC))


# --- MODIFIED --- Helper function to determine required documents
def get_required_documents_list(degree_type, nationality):
    """
    Returns a list of required document dicts {name: '...', type: '...'}
    based on the degree type and student's nationality.
    """
    # TRANSLATED document names
    # --- Base documents required for everyone ---
    base_docs = [
        {"name": "صورة شخصية حديثة", "type": "photo"},
        {"name": "شهادة الميلاد", "type": "birth_certificate"},
        {"name": "شهادة الثانوية العامة", "type": "high_school_cert"},
        {"name": "شهادة البكالوريوس", "type": "bachelor_cert"},
        {"name": "السجل الأكاديمي (كشف الدرجات)", "type": "transcript"},
    ]

    # --- Degree-specific documents ---
    if degree_type in ['Master', 'PhD']:
        base_docs.extend([
            {"name": "خطاب توصية (1)", "type": "recommendation_1"},
            {"name": "خطاب توصية (2)", "type": "recommendation_2"},
            {"name": "السيرة الذاتية", "type": "cv"}
        ])
    if degree_type == 'PhD':
         base_docs.extend([
            {"name": "شهادة الماجستير", "type": "master_cert"},
            {"name": "مقترح بحثي", "type": "research_proposal"}
         ])

    # --- Nationality-specific documents ---
    # The value from the form is 'Egyptian'. We check against this.
    if nationality == 'Egyptian':
        base_docs.append({"name": "بطاقة الرقم القومي (وجه وظهر)", "type": "national_id"})
        # You can add military status for males here if it's a required document
        # base_docs.append({"name": "شهادة الموقف من التجنيد", "type": "military_status"})
    else:  # International / وافد
        base_docs.extend([
            {"name": "جواز السفر (ساري المفعول)", "type": "passport"},
            {"name": "تصديق شهادة المؤهل السابق", "type": "attested_cert"},
            {"name": "شهادة إجادة اللغة الإنجليزية (إن وجدت)", "type": "english_proficiency"}
        ])

    return base_docs


@app.route('/student/documents')
@login_required
def student_documents():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    documents = Document.query.filter_by(user_id=current_user.id).all()
    applications = Application.query.filter_by(user_id=current_user.id).all()

    return render_template('student/documents.html', documents=documents, applications=applications)

# MODIFIED: This route now handles creating AND updating documents
@app.route('/student/documents/upload', methods=['GET', 'POST'])
@login_required
def student_upload_document():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    class DocumentForm(FlaskForm):
        pass  # Empty form just for CSRF protection
    form = DocumentForm()

    # Check if this is a GET request for updating a specific document
    doc_id_to_update = request.args.get('update', type=int)
    document_to_update = None
    if doc_id_to_update:
        document_to_update = Document.query.filter(
            Document.id == doc_id_to_update,
            Document.user_id == current_user.id
        ).first_or_404()

    if request.method == 'POST' and form.validate_on_submit():
        if 'document' not in request.files or not request.files['document'].filename:
            # TRANSLATED
            flash('لم يتم تحديد ملف للرفع.', 'danger')
            return redirect(request.url)

        file = request.files['document']
        
        # This hidden field from the form determines if we are in update mode.
        doc_id_from_form = request.form.get('document_id_to_update', type=int)

        if doc_id_from_form:
            # --- UPDATE LOGIC ---
            doc = Document.query.filter_by(id=doc_id_from_form, user_id=current_user.id).first_or_404()

            # Prepare to delete the old file after a successful update
            old_file_path_full = None
            if doc.file_path:
                # Use os.path.basename to reliably get just the filename. This is safer.
                old_filename = os.path.basename(doc.file_path)
                old_file_path_full = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)

            # Save the new file
            filename = secure_filename(file.filename)
            timestamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
            new_filename = f"{current_user.id}_{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))

            # Update the database record with the new file path and reset status
            doc.file_path = f"uploads/{new_filename}"
            doc.uploaded_at = datetime.now(UTC)
            doc.status = 'تم الرفع'  # Reset status for potential re-review by admin
            db.session.commit()

            # Now that the DB is updated, delete the old file from storage
            if old_file_path_full and os.path.exists(old_file_path_full):
                try:
                    os.remove(old_file_path_full)
                    app.logger.info(f"Successfully removed old file: {old_file_path_full}")
                except Exception as e:
                    app.logger.error(f"Could not remove old file '{old_file_path_full}': {e}")
            
            # TRANSLATED
            flash('تم تحديث المستند بنجاح!', 'success')
            return redirect(url_for('student_documents'))
        else:
            # --- CREATE NEW DOCUMENT LOGIC ---
            document_type = request.form.get('document_type')
            application_id = request.form.get('application_id')

            if not document_type:
                # TRANSLATED
                flash('يجب اختيار نوع المستند.', 'danger')
                return redirect(request.url)

            filename = secure_filename(file.filename)
            timestamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
            new_filename = f"{current_user.id}_{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))

            new_document = Document(
                user_id=current_user.id,
                application_id=application_id if application_id else None,
                name=document_type,
                file_path=f"uploads/{new_filename}",
                status='تم الرفع'
            )
            db.session.add(new_document)
            db.session.commit()
            
            # TRANSLATED
            flash('تم رفع المستند بنجاح!', 'success')
            return redirect(url_for('student_documents'))

    # --- GET REQUEST ---
    # For a new upload or an update, we pass necessary data to the template.
    applications = Application.query.filter_by(user_id=current_user.id).all()
    # The template 'upload_document.html' will use the 'document_to_update' object
    # to render itself in "update mode."
    return render_template('student/upload_document.html', 
                           form=form, 
                           applications=applications, 
                           document_to_update=document_to_update)

@app.route('/student/document/delete/<int:doc_id>', methods=['POST'])
@login_required
def student_delete_document(doc_id):
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    document = Document.query.get_or_404(doc_id)

    # Ensure this document belongs to the current user
    if document.user_id != current_user.id:
        # TRANSLATED
        flash('الوصول مرفوض', 'danger')
        return redirect(url_for('student_documents'))

    # Get the file path to remove it from storage
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.file_path.replace('uploads/', ''))

    # Delete the document from the database
    db.session.delete(document)
    db.session.commit()

    # Try to remove the file (if it exists)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        # Log the error but continue (document is already deleted from database)
        print(f"Error removing file: {e}")
    # TRANSLATED
    flash('تم حذف المستند بنجاح', 'success')
    return redirect(url_for('student_documents'))

@app.route('/student/certificates')
@login_required
def student_certificates():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    certificates = Certificate.query.filter_by(user_id=current_user.id).all()
    return render_template('student/certificates.html', certificates=certificates)


# Keep the original route
@app.route('/student/certificates/request', methods=['GET', 'POST'])
@login_required
def student_request_certificate():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    # Add a FlaskForm for CSRF protection
    class CertificateForm(FlaskForm):
        pass  # Empty form just for CSRF protection

    form = CertificateForm()

    if request.method == 'POST' and form.validate_on_submit():
        # Create new certificate request
        certificate = Certificate(
            user_id=current_user.id,
            type=request.form.get('certificate_type'), # Assuming type comes from form (potentially Arabic)
            purpose=request.form.get('purpose'), # Assuming purpose comes from form (potentially Arabic)
            copies=int(request.form.get('copies', 1)),
            # TRANSLATED status
            status='بانتظار الدفع', # Pending Payment
            cert_id=f"CERT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}", # Keep format
            request_date=datetime.now(UTC)
        )

        db.session.add(certificate)
        db.session.commit()
        # TRANSLATED
        flash('تم تقديم طلب الشهادة بنجاح! الرجاء المتابعة للدفع.', 'success') # Added payment info
        return redirect(url_for('student_certificates'))

    return render_template('student/request_certificate.html', form=form)

@app.route('/student/support')
@login_required
def student_support():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    tickets = Ticket.query.filter_by(user_id=current_user.id).order_by(Ticket.created_at.desc()).all()
    return render_template('student/support.html', tickets=tickets)

@app.route('/student/support/new', methods=['GET', 'POST'])
@login_required
def student_new_ticket():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')

        if not subject or not message:
            # TRANSLATED
            flash('يرجى ملء جميع الحقول', 'danger')
            return redirect(request.url)

        # Generate a unique ticket ID
        ticket_count = Ticket.query.count() + 1
        ticket_id = f"TKT-{ticket_count:03d}" # Keep format

        # Create new ticket
        new_ticket = Ticket(
            ticket_id=ticket_id,
            user_id=current_user.id,
            subject=subject,
            # TRANSLATED status
            status='مفتوحة' # Open
        )

        db.session.add(new_ticket)
        # db.session.commit() # Commit after adding message
        db.session.flush() # Flush to get new_ticket.id

        # Add the first message
        first_message = TicketMessage(
            ticket_id=new_ticket.id,
            sender='Student', # Keep 'Student' for logic, or use 'طالب'? Keep for consistency.
            message=message
        )

        db.session.add(first_message)
        db.session.commit() # Commit both ticket and message
        # TRANSLATED
        flash('تم إرسال تذكرة الدعم بنجاح!', 'success')
        return redirect(url_for('student_support'))

    return render_template('student/new_ticket.html')

@app.route('/student/support/<int:ticket_id>')
@login_required
def student_ticket_detail(ticket_id):
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    ticket = Ticket.query.get_or_404(ticket_id)

    # Ensure this ticket belongs to the current user
    if ticket.user_id != current_user.id:
        # TRANSLATED
        flash('الوصول مرفوض', 'danger')
        return redirect(url_for('student_support'))

    return render_template('student/ticket_detail.html', ticket=ticket)

@app.route('/student/support/reply/<int:ticket_id>', methods=['POST'])
@login_required
def student_ticket_reply(ticket_id):
    if current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'})

    try:
        ticket = Ticket.query.get_or_404(ticket_id)

        # Ensure ticket belongs to current user
        if ticket.user_id != current_user.id:
            # TRANSLATED
            return jsonify({'success': False, 'message': 'الوصول مرفوض'})

        message_text = request.form.get('message')
        if not message_text:
            # TRANSLATED
            return jsonify({'success': False, 'message': 'لا يمكن أن تكون الرسالة فارغة'})

        # Create new message
        new_message = TicketMessage(
            ticket_id=ticket.id,
            sender='Student', # Keep 'Student' for consistency
            message=message_text,
            created_at=datetime.now(UTC)
        )

        # Create notification for admins
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            # TRANSLATED notification message
            notification = Notification(
                user_id=admin.id,
                message=f'رد جديد على التذكرة {ticket.ticket_id} من {current_user.full_name}',
                url=url_for('admin_ticket_detail', ticket_id=ticket.id)
            )
            db.session.add(notification)

        db.session.add(new_message)

        # Update ticket status if it was closed by student? Maybe set to 'In Progress' or keep 'Open'?
        # Let's set it back to 'In Progress' if the student replies to a closed ticket.
        # TRANSLATED statuses
        if ticket.status == 'مغلقة':
             ticket.status = 'قيد المعالجة' # Re-open to In Progress

        db.session.commit()
        # TRANSLATED success message
        return jsonify({
            'success': True,
            'message': 'تم إرسال الرد بنجاح',
            'data': {
                'message': message_text,
                'created_at': new_message.created_at.strftime('%Y-%m-%d %H:%M'),
                'sender': 'Student' # Keep sender as 'Student' in response
            }
        })

    except Exception as e:
        db.session.rollback()
        # TRANSLATED part of message
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'})

@app.route('/student/payments/<int:app_id>', methods=['GET', 'POST'])
@login_required
def student_payment(app_id):
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    application = Application.query.get_or_404(app_id)

    # Create empty form for CSRF protection
    form = FlaskForm()

    # Ensure this application belongs to the current user
    if application.user_id != current_user.id:
        # TRANSLATED
        flash('الوصول مرفوض', 'danger')
        return redirect(url_for('student_applications'))

    # --- MODIFIED --- Calculate fee based on nationality (Check against 'Egyptian')
    fee = 1500 if current_user.nationality != 'Egyptian' else 600

    if request.method == 'POST' and form.validate_on_submit():
        # Create payment record
        new_payment = Payment(
            user_id=current_user.id,
            application_id=application.id,
            amount=fee,
            # TRANSLATED payment method
            payment_method='محاكاة', # Simulation
            transaction_id=f"TXN-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}" # Keep format
        )
        db.session.add(new_payment)

        # Update application payment status
        # TRANSLATED status
        application.payment_status = 'مدفوع' # Paid

        # --- NOTIFICATION & EMAIL ---
        # Notify all admins that a payment has been made
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            notification = Notification(
                user_id=admin.id,
                message=f'أكمل الطالب {current_user.full_name} الدفع للطلب رقم {application.app_id}.',
                url=url_for('admin_application_details', application_id=application.id)
            )
            db.session.add(notification)
        
        db.session.commit()
        # TRANSLATED
        flash('تمت معالجة الدفع بنجاح!', 'success')
        return redirect(url_for('student_applications'))

    # GET Request
    return render_template('student/payment.html',
                         application=application,
                         fee=fee,
                         form=form) # Pass the form for CSRF

@app.route('/student/certificate_payment/<int:cert_id>', methods=['GET', 'POST'])
@login_required
def student_certificate_payment(cert_id):
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    certificate = Certificate.query.get_or_404(cert_id)

    # Create empty form for CSRF protection
    class PaymentForm(FlaskForm):
        pass
    form = PaymentForm()

    # Ensure certificate belongs to current user
    if certificate.user_id != current_user.id:
        # TRANSLATED
        flash('الوصول مرفوض', 'danger')
        return redirect(url_for('student_certificates'))

    # Get certificate fee (assuming a fixed fee for now)
    # Use a setting or constant if possible
    certificate_fee = 200 # Example fee
    total_fee = certificate_fee * certificate.copies

    if request.method == 'POST' and form.validate_on_submit():
         # Simulate Payment
         # Create payment record
         new_payment = Payment(
             user_id=current_user.id,
             certificate_id=certificate.id, # Link payment to certificate
             amount=total_fee, # Fee per copy
             # TRANSLATED payment method
             payment_method='محاكاة', # Simulation
             transaction_id=f"CERT-TXN-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}" # Keep format
         )
         db.session.add(new_payment)

         # Update certificate status from 'Pending Payment' to 'Processing'
         # TRANSLATED statuses
         if certificate.status == 'بانتظار الدفع':
             certificate.status = 'قيد التجهيز' # Processing
        
         # --- NOTIFICATION & EMAIL ---
         # Notify all admins that a certificate payment has been made
         admins = User.query.filter_by(role='admin').all()
         for admin in admins:
             notification = Notification(
                 user_id=admin.id,
                 message=f'دفع الطالب {current_user.full_name} رسوم الشهادة رقم {certificate.cert_id}.',
                 url=url_for('admin_certificates')
             )
             db.session.add(notification)

         db.session.commit()
         # TRANSLATED
         flash(f'تم دفع رسوم الشهادة بنجاح ({total_fee} جنيه). الشهادة الآن قيد التجهيز.', 'success')
         return redirect(url_for('student_certificates'))

    # GET Request
    # Make sure status is Pending Payment before showing payment page
    # TRANSLATED status
    if certificate.status != 'بانتظار الدفع':
        flash('تم دفع رسوم هذه الشهادة بالفعل أو أنها ليست بانتظار الدفع.', 'info')
        return redirect(url_for('student_certificates'))

    return render_template('student/certificate_payment.html',
                         certificate=certificate,
                         fee=total_fee, # Calculate total fee
                         form=form)


@app.route('/student/settings')
@login_required
def student_settings():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    # Create a form for CSRF protection
    class SettingsForm(FlaskForm):
        pass

    form = SettingsForm()

    return render_template('student/settings.html', form=form)

@app.route('/student/settings/update', methods=['POST'])
@login_required
def student_update_settings():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    full_name = request.form.get('full_name')
    phone = request.form.get('phone')

    current_user.full_name = full_name
    current_user.phone = phone

    db.session.commit()
    # TRANSLATED
    flash('تم تحديث الإعدادات بنجاح!', 'success')
    return redirect(url_for('student_settings'))

@app.route('/student/change_password', methods=['POST'])
@login_required
def student_change_password():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not current_user.check_password(current_password):
        # TRANSLATED
        flash('كلمة المرور الحالية غير صحيحة', 'danger')
        return redirect(url_for('student_settings'))

    if not new_password or len(new_password) < 6: # Add basic validation
        # TRANSLATED
         flash('كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل', 'danger')
         return redirect(url_for('student_settings'))

    if new_password != confirm_password:
        # TRANSLATED
        flash('كلمتا المرور الجديدتان غير متطابقتين', 'danger')
        return redirect(url_for('student_settings'))

    current_user.set_password(new_password)
    db.session.commit()
    # TRANSLATED
    flash('تم تغيير كلمة المرور بنجاح!', 'success')
    return redirect(url_for('student_settings'))

@app.route('/mark_notifications_read', methods=['POST'])
@login_required
def mark_notifications_read():
    notifications = Notification.query.filter_by(user_id=current_user.id, read=False).all()

    for notification in notifications:
        notification.read = True

    db.session.commit()
    return jsonify({'success': True})

@app.route('/student/close_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def student_close_ticket(ticket_id):
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    ticket = Ticket.query.get_or_404(ticket_id)

    # Ensure this ticket belongs to the current user
    if ticket.user_id != current_user.id:
        # TRANSLATED
        flash('الوصول مرفوض', 'danger')
        return redirect(url_for('student_support'))

    # TRANSLATED status
    ticket.status = 'مغلقة' # Closed
    db.session.commit()
    # TRANSLATED
    flash('تم إغلاق التذكرة بنجاح', 'success')
    return redirect(url_for('student_ticket_detail', ticket_id=ticket.id))

@app.route('/student/update_notification_preferences', methods=['POST'])
@login_required
def student_update_notification_preferences():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    # TRANSLATED
    flash('تم تحديث تفضيلات الإشعارات بنجاح!', 'success')
    return redirect(url_for('student_settings'))

# Add this new route for student profile
@app.route('/student/profile', methods=['GET'])
@login_required
def student_profile():
    """Display student profile page"""
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    # Create an empty form instance for CSRF protection
    form = FlaskForm()

    # Get student ID if available from the StudentID table
    student_id_obj = StudentID.query.join(Application).filter(
        Application.user_id == current_user.id
    ).first()
    student_id = student_id_obj.student_id if student_id_obj else None

    # Get program if available - use Application relationship from StudentID
    program = None
    if student_id_obj and student_id_obj.application:
        program = student_id_obj.application.program  # This should have the Arabic name if set correctly

    # Calculate cumulative GPA
    cumulative_gpa = calculate_gpa(current_user.id)

    return render_template('student/profile.html',
                           form=form,
                           student_id=student_id,
                           program=program,
                           cumulative_gpa=cumulative_gpa)


# Add a new route for updating profile
@app.route('/student/profile/update', methods=['POST'])
@login_required
def student_update_profile():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    # Use a simple form for CSRF validation
    form = FlaskForm()
    if form.validate_on_submit():
        # Get data from the form
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        nationality = request.form.get('nationality')
        gender = request.form.get('gender')
        education = request.form.get('education')
        military_status = request.form.get('military_status')

        # Update user object
        user = current_user
        if full_name: user.full_name = full_name
        if email: user.email = email
        user.phone = phone # Allow clearing the field
        if nationality: user.nationality = nationality
        if gender: user.gender = gender
        if education: user.education = education

        # Only update military status if it was submitted
        if military_status:
            user.military_status = military_status

        try:
            db.session.commit()
            flash('تم تحديث الملف الشخصي بنجاح!', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating profile for user {user.id}: {str(e)}")
            flash(f'حدث خطأ أثناء تحديث الملف الشخصي: {str(e)}', 'danger')

        return redirect(url_for('student_profile'))
    else:
        # This will catch CSRF errors
        flash('حدث خطأ في التحقق من النموذج. يرجى المحاولة مرة أخرى.', 'danger')
        return redirect(url_for('student_profile'))


# Add this new command function
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database and create admin user."""
    db.create_all()

    # Check if admin user exists
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            email='admin@example.com',
            full_name='Admin User', # Keep name as is
            role='admin',
            is_verified=True # Admins are auto-verified
        )
        admin.set_password('adminpassword') # Keep password as is
        db.session.add(admin)
        db.session.commit()
        # TRANSLATED
        click.echo('تم تهيئة قاعدة البيانات وإنشاء المستخدم المسؤول.')
    else:
        # TRANSLATED
        click.echo('قاعدة البيانات مهيأة بالفعل.')




@app.route('/admin/projects')
@login_required
def admin_projects():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('admin/projects.html', projects=projects)



@app.route('/admin/projects/new', methods=['GET', 'POST'])
@login_required
def admin_new_project():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    # Add CSRF protection via a simple form
    class ProjectForm(FlaskForm):
        pass
    form = ProjectForm()

    if request.method == 'POST' and form.validate_on_submit():
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        url = request.form.get('url')
        is_popular = 'is_popular' in request.form
        is_active = 'is_active' in request.form

        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                # Validate file extension
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                if '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:

                    # Create unique filename
                    timestamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
                    original_filename = secure_filename(file.filename)
                    new_filename = f"project_{timestamp}_{original_filename}" # Keep format

                    # Ensure upload directory exists
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

                    # Save file
                    try:
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                        file.save(file_path)
                        image_path = 'uploads/' + new_filename # Keep format
                    except Exception as e:
                        # TRANSLATED
                        flash(f'خطأ في رفع الملف: {str(e)}', 'danger')
                        return render_template('admin/new_project.html', form=form) # Return with form
                else:
                    # TRANSLATED
                    flash('نوع ملف غير صالح. يرجى رفع ملف صورة.', 'danger')
                    return render_template('admin/new_project.html', form=form) # Return with form

        try:
            # Create new project
            new_project = Project(
                title=title,
                description=description,
                category=category,
                url=url,
                image_path=image_path,
                is_popular=is_popular,
                is_active=is_active,
                user_id=current_user.id # Associate with the admin who added it
            )

            db.session.add(new_project)
            db.session.commit()
            # TRANSLATED
            flash('تمت إضافة المشروع بنجاح!', 'success')
            return redirect(url_for('admin_projects'))

        except Exception as e:
            # If there's an error saving to database, delete uploaded file
            if image_path and 'new_filename' in locals():
                 try:
                     os.remove(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                 except Exception as file_err:
                      app.logger.error(f"Error removing uploaded file after DB error: {file_err}")

            db.session.rollback()
            # TRANSLATED
            flash(f'خطأ في إنشاء المشروع: {str(e)}', 'danger')
            # Render form again on error
            return render_template('admin/new_project.html', form=form)

    # GET request - show form
    return render_template('admin/new_project.html', form=form)


@app.route('/admin/projects/edit/<int:project_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_project(project_id):
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    project = Project.query.get_or_404(project_id)

    # Add CSRF protection via a simple form
    class ProjectEditForm(FlaskForm):
        pass
    form = ProjectEditForm()

    if request.method == 'POST' and form.validate_on_submit():
        project.title = request.form.get('title')
        project.description = request.form.get('description')
        project.category = request.form.get('category')
        project.url = request.form.get('url')
        project.is_popular = 'is_popular' in request.form
        project.is_active = 'is_active' in request.form

        # Handle file upload if there's a new image
        if 'project_image' in request.files:
            file = request.files['project_image']
            if file and file.filename != '': # Check if a file was actually selected
                # Validate extension
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                if '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:

                    filename = secure_filename(file.filename)
                    # Create a unique filename with timestamp
                    timestamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
                    new_filename = f"project_{timestamp}_{filename}" # Keep format

                    try:
                         file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                         file.save(file_path)

                         # Delete the old image if it exists and is different
                         if project.image_path and project.image_path != f"uploads/{new_filename}":
                             old_file_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                                         project.image_path.replace('uploads/', ''))
                             try:
                                 if os.path.exists(old_file_path):
                                     os.remove(old_file_path)
                                     app.logger.info(f"Removed old project image: {old_file_path}")
                             except Exception as e:
                                 app.logger.error(f"Error removing old image: {e}")

                         project.image_path = f"uploads/{new_filename}" # Keep format
                    except Exception as e:
                          # TRANSLATED
                          flash(f'خطأ في رفع الملف الجديد: {str(e)}', 'danger')
                          # Don't redirect, show form again with error
                          return render_template('admin/edit_project.html', project=project, form=form)
                else:
                     # TRANSLATED
                     flash('نوع ملف الصورة الجديد غير صالح.', 'danger')
                     return render_template('admin/edit_project.html', project=project, form=form)


        try:
            db.session.commit()
            # TRANSLATED
            flash('تم تحديث المشروع بنجاح!', 'success')
            return redirect(url_for('admin_projects'))
        except Exception as e:
             db.session.rollback()
             # TRANSLATED
             flash(f'خطأ في تحديث المشروع: {str(e)}', 'danger')
             return render_template('admin/edit_project.html', project=project, form=form)


    # GET request
    return render_template('admin/edit_project.html', project=project, form=form)

@app.route('/admin/projects/delete/<int:project_id>', methods=['POST'])
@login_required
def admin_delete_project(project_id):
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'})

    project = Project.query.get_or_404(project_id)

    # Delete image file if it exists
    image_filename = None
    if project.image_path:
        image_filename = project.image_path.replace('uploads/', '')
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                app.logger.info(f"Deleted project image file: {file_path}")
        except Exception as e:
            app.logger.error(f"Error removing project image file {file_path}: {e}")

    try:
        db.session.delete(project)
        db.session.commit()
        # TRANSLATED success message (will be shown via JS)
        return jsonify({'success': True, 'message': 'تم حذف المشروع بنجاح'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting project {project_id} from DB: {e}")
        # TRANSLATED error message
        return jsonify({'success': False, 'message': f'خطأ أثناء حذف المشروع: {str(e)}'})


@app.route('/admin/projects/toggle-status/<int:project_id>', methods=['POST'])
@login_required
def admin_toggle_project_status(project_id):
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'})

    project = Project.query.get_or_404(project_id)
    status_type = request.form.get('status_type')
    status_message = "" # For the response

    try:
        if status_type == 'active':
            project.is_active = not project.is_active
            # TRANSLATED status message parts
            status_message = 'نشط' if project.is_active else 'غير نشط'
        elif status_type == 'popular':
            project.is_popular = not project.is_popular
            # TRANSLATED status message parts
            status_message = 'شائع' if project.is_popular else 'غير شائع'
        else:
            # TRANSLATED error
             return jsonify({'success': False, 'message': 'نوع الحالة غير معروف'})

        db.session.commit()
        # TRANSLATED success message parts
        return jsonify({'success': True, 'status': status_message, 'message': f'تم تغيير حالة المشروع إلى {status_message}'})
    except Exception as e:
         db.session.rollback()
         app.logger.error(f"Error toggling project {project_id} status: {e}")
         # TRANSLATED error
         return jsonify({'success': False, 'message': f'خطأ في تغيير حالة المشروع: {str(e)}'})


@app.route('/projects')
def projects():
    # Get all active projects
    projects = Project.query.filter_by(is_active=True).order_by(Project.created_at.desc()).all()

    # Get unique categories
    categories = db.session.query(Project.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]

    return render_template('projects.html',
                         projects=projects,
                         categories=categories)

# Register the command with Flask CLI
app.cli.add_command(init_db_command)

@app.context_processor
def inject_now():
    return {'now': datetime.now(UTC)}

@app.route('/news')
def news():
    news_items = News.query.order_by(News.date.desc()).all()
    return render_template('news.html', news_items=news_items)

@app.route('/admin/news')
@login_required
def admin_news():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    news_items = News.query.order_by(News.date.desc()).all()
    return render_template('admin/news.html', news_items=news_items)

@app.route('/admin/news/add', methods=['GET', 'POST'])
@login_required
def admin_news_add():
    if not current_user.is_admin():
         return redirect(url_for('student_dashboard'))

    class NewsForm(FlaskForm):
        pass
    form = NewsForm()

    if request.method == 'POST' and form.validate_on_submit():
        title = request.form.get('title')
        description = request.form.get('description')
        news_type = request.form.get('type') # 'news' or 'announcement'
        try:
            date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
        except (ValueError, TypeError):
             # TRANSLATED error
             flash('صيغة التاريخ غير صالحة. استخدم YYYY-MM-DD.', 'danger')
             return render_template('admin/news_add.html', form=form)


        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                 # Validate extension
                 allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                 if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                     filename = secure_filename(file.filename)
                     timestamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
                     new_filename = f"news_{timestamp}_{filename}" # Keep format
                     try:
                          file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                          image_path = f"uploads/{new_filename}" # Keep format
                     except Exception as e:
                          # TRANSLATED error
                          flash(f'خطأ في رفع صورة الخبر: {str(e)}', 'danger')
                          return render_template('admin/news_add.html', form=form)
                 else:
                      # TRANSLATED error
                      flash('نوع ملف الصورة غير صالح.', 'danger')
                      return render_template('admin/news_add.html', form=form)

        # Inside the admin_news_add route in run.py

        try:
            # --- THE FIX IS HERE ---
            # Manually set the timestamps before creating the object
            now_utc = datetime.now(UTC)

            news_item = News(
                title=title,
                description=description,
                type=news_type,
                date=date,
                image_path=image_path,
                is_active=True, # Default to active
                # Explicitly set the timestamp fields
                created_at=now_utc,
                updated_at=now_utc
            )
            # --- END OF FIX ---

            db.session.add(news_item)
            db.session.commit()
            # TRANSLATED success
            flash('تمت إضافة الخبر / الإعلان بنجاح!', 'success')
            return redirect(url_for('admin_news'))
        except Exception as e:
             db.session.rollback()
             # TRANSLATED error
             flash(f'خطأ في إضافة الخبر / الإعلان: {str(e)}', 'danger')
             # Remove uploaded file if DB save failed
             if image_path and 'new_filename' in locals():
                  try:
                      os.remove(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                  except Exception: pass
             return render_template('admin/news_add.html', form=form)


    return render_template('admin/news_add.html', form=form)

@app.route('/admin/news/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_news_edit(id):
    if not current_user.is_admin():
         return redirect(url_for('student_dashboard'))

    class NewsForm(FlaskForm):
        pass
    form = NewsForm()
    news_item = News.query.get_or_404(id)

    if request.method == 'POST' and form.validate_on_submit():
        news_item.title = request.form.get('title')
        news_item.description = request.form.get('description')
        news_item.type = request.form.get('type')
        news_item.is_active = 'is_active' in request.form # Add active toggle

        try:
            news_item.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
        except (ValueError, TypeError):
             # TRANSLATED error
             flash('صيغة التاريخ غير صالحة. استخدم YYYY-MM-DD.', 'danger')
             return render_template('admin/news_edit.html', form=form, news=news_item)


        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Validate extension
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # Delete old image if exists
                    old_image_path_to_delete = None
                    if news_item.image_path:
                         old_image_path_to_delete = os.path.join(app.config['UPLOAD_FOLDER'],
                                                     news_item.image_path.replace('uploads/', ''))

                    filename = secure_filename(file.filename)
                    timestamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
                    new_filename = f"news_{timestamp}_{filename}" # Keep format
                    try:
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                        news_item.image_path = f"uploads/{new_filename}" # Keep format

                        # Delete old image *after* new one is saved
                        if old_image_path_to_delete and os.path.exists(old_image_path_to_delete):
                            os.remove(old_image_path_to_delete)
                            app.logger.info(f"Removed old news image: {old_image_path_to_delete}")
                    except Exception as e:
                         # TRANSLATED error
                         flash(f'خطأ في رفع صورة الخبر الجديدة: {str(e)}', 'danger')
                         return render_template('admin/news_edit.html', form=form, news=news_item)
                else:
                     # TRANSLATED error
                     flash('نوع ملف الصورة الجديد غير صالح.', 'danger')
                     return render_template('admin/news_edit.html', form=form, news=news_item)

        try:
            news_item.updated_at = datetime.now(UTC)
            db.session.commit()
            # TRANSLATED success
            flash('تم تحديث الخبر / الإعلان بنجاح!', 'success')
            return redirect(url_for('admin_news'))
        except Exception as e:
             db.session.rollback()
             # TRANSLATED error
             flash(f'خطأ في تحديث الخبر / الإعلان: {str(e)}', 'danger')
             return render_template('admin/news_edit.html', form=form, news=news_item)


    # GET Request: Format date for input field
    date_value = news_item.date.strftime('%Y-%m-%d') if news_item.date else ''
    return render_template('admin/news_edit.html', form=form, news=news_item, date_value=date_value)


@app.route('/admin/news/delete/<int:id>', methods=['POST'])
@login_required
def admin_news_delete(id):
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'})

    news_item = News.query.get_or_404(id)

    # Delete image file if exists
    image_filename = None
    if news_item.image_path:
        image_filename = news_item.image_path.replace('uploads/', '')
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
                app.logger.info(f"Deleted news image file: {image_path}")
            except Exception as e:
                app.logger.error(f"Error removing news image file {image_path}: {e}")

    try:
        db.session.delete(news_item)
        db.session.commit()
        # TRANSLATED success (for JS)
        return jsonify({'success': True, 'message': 'تم حذف الخبر / الإعلان بنجاح'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting news item {id} from DB: {e}")
        # TRANSLATED error (for JS)
        return jsonify({'success': False, 'message': f'خطأ أثناء حذف الخبر / الإعلان: {str(e)}'})


@app.route('/about')
def about():
    """Display about page"""
    return render_template('about.html')

@app.route('/contact')
def contact():
    """Display contact page"""
    return render_template('contact.html')

@app.route('/search')
def search():
    """Handle search functionality"""
    query = request.args.get('q', '')
    # Implement search logic here
    results = []  # Replace with actual search results
    return render_template('search.html', results=results, query=query)

@app.route('/faq')
def faq():
    """Display FAQ page"""
    return render_template('faq.html')

@app.route('/privacy')
def privacy():
    """Display privacy policy page"""
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    """Display terms of service page"""
    return render_template('terms.html')

@app.route('/student/courses')
@login_required
def student_courses():
    """Displays enrolled and available courses for the student, handling auto-enrollment."""
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    user_id = current_user.id
    current_academic_year = get_current_academic_year() # Get current academic year
    active_application = None # Initialize outside the try block

    # --- Automatic Semester Enrollment Logic ---
    try:
        # 1. Find the student's active/enrolled application and the semester they applied for
        # TRANSLATED status
        active_application = Application.query.filter(
            Application.user_id == user_id,
            Application.status == 'مسجل' # Enrolled
        ).options(
            selectinload(Application.program_relation) # Eager load program
        ).order_by(Application.date_submitted.desc()).first()

        if active_application and active_application.program_relation and active_application.semester:
            program = active_application.program_relation
            # Determine target semester name based on application data
            target_semester_number = active_application.semester # Keep the number '1' or '2'
            # TRANSLATED semester names
            target_semester_name = "الفصل الدراسي الأول" if target_semester_number == '1' else "الفصل الدراسي الثاني" if target_semester_number == '2' else None

            if target_semester_name and target_semester_number: # Check both number and name
                app.logger.info(f"User {user_id} enrolled in program {program.id}. Checking auto-enrollment for {target_semester_name} ({current_academic_year}).")

                # 2. Identify courses for the target semester in this program using the NUMBER
                # Assuming ProgramCourse.semester stores 1 or 2
                target_semester_program_courses = ProgramCourse.query.filter_by(
                    program_id=program.id,
                    semester=int(target_semester_number) # Use the integer number for query
                ).all()

                target_course_ids = [pc.course_id for pc in target_semester_program_courses]

                if target_course_ids:
                    # 3. Check if student is already enrolled in ANY of these target semester courses for the CURRENT academic year
                    existing_enrollment_this_year = CourseEnrollment.query.filter(
                        CourseEnrollment.student_id == user_id,
                        CourseEnrollment.course_id.in_(target_course_ids),
                        CourseEnrollment.academic_year == current_academic_year # Crucial check for idempotency per year
                    ).first()

                    # 4. If no existing enrollment found for this semester's courses in this academic year, enroll them
                    if not existing_enrollment_this_year:
                        enrollments_added = 0
                        for course_id in target_course_ids:
                            # Double-check just in case before adding
                            already_exists = CourseEnrollment.query.filter_by(
                                student_id=user_id,
                                course_id=course_id,
                                academic_year=current_academic_year
                            ).first()

                            if not already_exists:
                                new_enrollment = CourseEnrollment(
                                    student_id=user_id,
                                    course_id=course_id,
                                    program_id=program.id, # Store program context
                                    enrollment_date=datetime.now(UTC),
                                    # TRANSLATED status
                                    status='مسجل', # Enrolled status for course
                                    semester=target_semester_name, # Store semester name for display consistency
                                    academic_year=current_academic_year # Store academic year context
                                )
                                db.session.add(new_enrollment)
                                enrollments_added += 1

                        if enrollments_added > 0:
                            db.session.commit()
                            # TRANSLATED flash message
                            flash(f'تم تسجيلك تلقائيًا في {enrollments_added} مقرر دراسي لـ {target_semester_name} للعام الدراسي {current_academic_year}.', 'success')
                            app.logger.info(f"User {user_id} auto-enrolled in {enrollments_added} courses for {target_semester_name} ({current_academic_year}), program {program.id}.")
                        else:
                             app.logger.info(f"User {user_id} already enrolled in {target_semester_name} courses for {current_academic_year}, program {program.id}. No auto-enrollment needed.")
                    else:
                        app.logger.info(f"User {user_id} already has enrollments for {target_semester_name} ({current_academic_year}). Skipping auto-enrollment.")
                else:
                    # Use the number in the log message for clarity on what was queried
                    app.logger.warning(f"No courses found defined for Program ID {program.id}, Semester Number: {target_semester_number}.")
            else:
                 app.logger.warning(f"Could not determine target semester from application {active_application.id} (semester value: {active_application.semester}). Skipping auto-enrollment.")
        else:
            # Log reasons for skipping auto-enrollment if application details are missing
            if not active_application:
                 app.logger.info(f"User {user_id} has no 'Enrolled' application. Skipping auto-enrollment.")
            elif not active_application.program_relation:
                 app.logger.warning(f"Application {active_application.id if active_application else 'N/A'} for user {user_id} has no linked program. Skipping auto-enrollment.")
            elif not active_application.semester:
                 app.logger.warning(f"Application {active_application.id if active_application else 'N/A'} for user {user_id} is missing the 'semester' value. Skipping auto-enrollment.")


    except Exception as e:
        db.session.rollback() # Rollback in case of error during auto-enrollment
        app.logger.error(f"Error during automatic enrollment check for user {user_id}: {str(e)}", exc_info=True)
        # TRANSLATED flash message
        flash('حدث خطأ أثناء التحقق من التسجيل التلقائي في المقررات.', 'danger')

    # --- Fetch Courses for Display (After potential auto-enrollment) ---
    enrolled_courses_data = []
    available_courses_data = []
    enrolled_course_ids = set()

    try:
        # Fetch enrolled courses with details
        enrolled_items = db.session.query(
            Course, CourseEnrollment
        ).join(
            CourseEnrollment, Course.id == CourseEnrollment.course_id
        ).filter(
            CourseEnrollment.student_id == user_id
        ).options(
            joinedload(CourseEnrollment.course) # Eager load course details
        ).order_by(
            CourseEnrollment.academic_year.desc(),
            CourseEnrollment.semester, # Assumes semester stores 'First Semester' etc.
            Course.code
        ).all()

        semester_map = {1: "الفصل الدراسي الأول", 2: "الفصل الدراسي الثاني"} # For available courses display

        for course, enrollment in enrolled_items:
            enrolled_courses_data.append({
                'course': course,
                'enrollment': enrollment,
                'semester': enrollment.semester, # Display semester from enrollment record (should be Arabic if saved correctly)
                'academic_year': enrollment.academic_year # Display year from enrollment record
            })
            enrolled_course_ids.add(course.id)

        # Fetch available courses (courses in the student's program they are NOT enrolled in for the current year)
        # Re-fetch active application to get program info if not already fetched or if it was None initially
        if not active_application:
             # TRANSLATED status
             active_application = Application.query.filter(
                Application.user_id == user_id,
                Application.status == 'مسجل' # Enrolled
             ).options(selectinload(Application.program_relation)).order_by(Application.date_submitted.desc()).first()

        if active_application and active_application.program_relation:
            program = active_application.program_relation
            # Get program course associations including the semester number
            program_courses = ProgramCourse.query.filter_by(program_id=program.id).all()
            program_course_details = {pc.course_id: pc.semester for pc in program_courses} # Map course_id to semester number

            # Find course IDs in the program but not in the enrolled set for the current year
            enrolled_this_year_ids = {
                enrollment.course_id for course, enrollment in enrolled_items
                if enrollment.academic_year == current_academic_year
            }

            available_course_ids = set(program_course_details.keys()) - enrolled_this_year_ids

            if available_course_ids:
                 available_items = Course.query.filter(
                     Course.id.in_(list(available_course_ids)),
                     Course.is_active == True # Only show active courses
                 ).order_by(
                     Course.code # Order by code primarily
                 ).all()

                 # Prepare available courses with semester info
                 temp_available = []
                 for course in available_items:
                     semester_num = program_course_details.get(course.id)
                     semester_name = semester_map.get(semester_num, "غير محدد") # Get Arabic semester name
                     # TODO: Add prerequisite check here if needed before showing as available
                     temp_available.append({
                         'course': course,
                         'semester': semester_name, # Use Arabic semester name
                         'semester_num': semester_num # Keep number for sorting
                     })

                 # Sort available courses by semester number then code
                 available_courses_data = sorted(temp_available, key=lambda x: (x['semester_num'] or 99, x['course'].code or ''))


    except Exception as e:
        app.logger.error(f"Error fetching course data for student {user_id}: {str(e)}", exc_info=True)
        # TRANSLATED flash message
        flash('حدث خطأ أثناء تحميل بيانات المقررات.', 'danger')

    return render_template(
        'student/courses.html',
        enrolled_courses=enrolled_courses_data,
        available_courses=available_courses_data
    )

# --- NEW --- API Endpoint for fetching required documents dynamically
@app.route('/api/required-documents')
@login_required
def api_required_documents():
    """
    Returns a JSON list of required documents for the current user
    based on their nationality and a given degree type.
    """
    try:
        degree_type = request.args.get('degree_type')
        if not degree_type:
            # TRANSLATED
            return jsonify({'success': False, 'message': 'نوع الدرجة مطلوب'}), 400

        user_nationality = current_user.nationality
        
        # Get the dynamic list of documents
        documents_list = get_required_documents_list(degree_type, user_nationality)
        
        app.logger.info(f"API: Required docs for user {current_user.id} (Nationality: {user_nationality}, Degree: {degree_type}) -> {len(documents_list)} docs.")

        return jsonify({
            'success': True,
            'documents': documents_list
        })
    except Exception as e:
        app.logger.error(f"Error in /api/required-documents: {str(e)}", exc_info=True)
        # TRANSLATED
        return jsonify({'success': False, 'message': 'حدث خطأ في الخادم'}), 500

# Modify the manual enrollment route to include academic year and semester
@app.route('/student/courses/enroll/<int:course_id>', methods=['POST'])
@login_required
def student_course_enroll(course_id): # Renamed function for clarity
    if current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'})

    course = Course.query.get_or_404(course_id)
    if not course.is_active:
         # TRANSLATED
         return jsonify({'success': False, 'message': 'هذا المقرر غير نشط حاليًا.'})

    user_id = current_user.id
    current_academic_year = get_current_academic_year()
    # TRANSLATED default semester
    target_semester_name = "غير محدد" # Unknown / Not specified
    program_id = None
    semester_map = {1: "الفصل الدراسي الأول", 2: "الفصل الدراسي الثاني"} # For setting enrollment semester

    # Find student's program and the semester this course belongs to
    # TRANSLATED status
    active_application = Application.query.filter_by(user_id=user_id, status='مسجل').first() # Enrolled
    if active_application:
        program_id = active_application.program_id
        # Get semester number from ProgramCourse mapping
        program_course_info = ProgramCourse.query.filter_by(program_id=program_id, course_id=course_id).first()
        if program_course_info and program_course_info.semester in semester_map:
            target_semester_name = semester_map[program_course_info.semester]
        else:
            app.logger.warning(f"Course {course_id} not found in ProgramCourse mapping for program {program_id} or invalid semester number. Semester set to '{target_semester_name}'.")
    else:
        app.logger.warning(f"Could not find active application for user {user_id} to determine program context for manual enrollment.")


    # Check if already enrolled in this course for the current academic year
    existing_enrollment = CourseEnrollment.query.filter_by(
        student_id=user_id, # Corrected variable name
        course_id=course_id,
        academic_year=current_academic_year
    ).first()

    if existing_enrollment:
        # TRANSLATED error message
        return jsonify({'success': False, 'message': f'أنت مسجل بالفعل في هذا المقرر ({course.code}) للعام الدراسي {current_academic_year}.'})

    # TODO: Add prerequisite checks before allowing enrollment
    # prereqs_met = check_prerequisites(user_id, course_id, current_academic_year)
    # if not prereqs_met:
    #     return jsonify({'success': False, 'message': 'لم يتم استيفاء المتطلبات السابقة.'}) # Prerequisites not met.

    try:
        # Create new enrollment record
        enrollment = CourseEnrollment(
            student_id=user_id, # Corrected variable name
            course_id=course_id,
            program_id=program_id, # Store program context
            enrollment_date=datetime.now(UTC),
            # TRANSLATED status
            status='مسجل', # Enrolled
            semester=target_semester_name, # Store Arabic semester name
            academic_year=current_academic_year # Store academic year context
        )
        db.session.add(enrollment)
        db.session.commit()
        app.logger.info(f"User {user_id} manually enrolled in course {course_id} ({course.code}) for {current_academic_year}.")
        # TRANSLATED flash message and success message
        flash(f'تم التسجيل بنجاح في مقرر {course.code}!', 'success')
        return jsonify({'success': True, 'message': f'تم التسجيل بنجاح في {course.code}'})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error manually enrolling user {user_id} in course {course_id}: {str(e)}", exc_info=True)
        # TRANSLATED error message
        return jsonify({'success': False, 'message': f'حدث خطأ أثناء التسجيل: {str(e)}'}), 500

@app.route('/admin/courses')
@login_required
def admin_courses():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    courses = Course.query.order_by(Course.code).all() # Order by code
    return render_template('admin/courses.html', courses=courses)

@app.route('/admin/courses/add', methods=['GET', 'POST'])
@login_required
def admin_course_add():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    # Use WTForms for validation and CSRF
    class CourseForm(FlaskForm):
        pass # Define fields in the template or add them here if needed
    form = CourseForm()

    if request.method == 'POST' and form.validate_on_submit():
        # Basic validation
        code = request.form.get('code')
        title = request.form.get('title')
        credits_str = request.form.get('credits')

        if not code or not title or not credits_str:
             # TRANSLATED error
             flash('رمز المقرر، العنوان، وعدد الساعات حقول مطلوبة.', 'danger')
             return render_template('admin/course_add.html', form=form)
        try:
             credits = int(credits_str)
             if credits <= 0: raise ValueError()
        except ValueError:
             # TRANSLATED error
             flash('عدد الساعات يجب أن يكون رقمًا صحيحًا موجبًا.', 'danger')
             return render_template('admin/course_add.html', form=form)

        # Check if code already exists
        if Course.query.filter_by(code=code).first():
            # TRANSLATED error
            flash(f'رمز المقرر "{code}" مستخدم بالفعل.', 'danger')
            return render_template('admin/course_add.html', form=form)


        course = Course(
            code=code.upper(), # Standardize code to uppercase
            title=title,
            description=request.form.get('description'),
            credits=credits,
            is_active=True # Default to active
        )

        try:
            db.session.add(course)
            db.session.commit()
            # TRANSLATED success
            flash('تمت إضافة المقرر بنجاح!', 'success')
            return redirect(url_for('admin_courses'))
        except Exception as e:
             db.session.rollback()
             app.logger.error(f"Error adding course: {e}")
             # TRANSLATED error
             flash(f'حدث خطأ أثناء إضافة المقرر: {str(e)}', 'danger')
             return render_template('admin/course_add.html', form=form)


    return render_template('admin/course_add.html', form=form)

@app.route('/admin/courses/edit/<int:course_id>', methods=['GET', 'POST'])
@login_required
def admin_course_edit(course_id):
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    course = Course.query.get_or_404(course_id)

    # Use WTForms for validation and CSRF
    class CourseEditForm(FlaskForm):
        pass
    form = CourseEditForm()

    if request.method == 'POST' and form.validate_on_submit():
        new_code = request.form.get('code')
        title = request.form.get('title')
        credits_str = request.form.get('credits')

        # Basic validation
        if not new_code or not title or not credits_str:
             # TRANSLATED error
             flash('رمز المقرر، العنوان، وعدد الساعات حقول مطلوبة.', 'danger')
             return render_template('admin/course_edit.html', course=course, form=form)
        try:
             credits = int(credits_str)
             if credits <= 0: raise ValueError()
        except ValueError:
             # TRANSLATED error
             flash('عدد الساعات يجب أن يكون رقمًا صحيحًا موجبًا.', 'danger')
             return render_template('admin/course_edit.html', course=course, form=form)

        # Check if new code conflicts with another course
        existing_course = Course.query.filter(Course.code == new_code, Course.id != course_id).first()
        if existing_course:
             # TRANSLATED error
             flash(f'رمز المقرر "{new_code}" مستخدم بالفعل لمقرر آخر.', 'danger')
             return render_template('admin/course_edit.html', course=course, form=form)


        course.code = new_code.upper() # Standardize code
        course.title = title
        course.description = request.form.get('description')
        course.credits = credits
        course.is_active = 'is_active' in request.form

        try:
            db.session.commit()
            # TRANSLATED success
            flash('تم تحديث المقرر بنجاح!', 'success')
            return redirect(url_for('admin_courses'))
        except Exception as e:
             db.session.rollback()
             app.logger.error(f"Error updating course {course_id}: {e}")
             # TRANSLATED error
             flash(f'حدث خطأ أثناء تحديث المقرر: {str(e)}', 'danger')
             return render_template('admin/course_edit.html', course=course, form=form)


    return render_template('admin/course_edit.html', course=course, form=form)

# ...existing code...

@app.route('/student/application/<int:application_id>/details')
@login_required
def student_application_details(application_id):
    """Return application details and documents for a specific application"""
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    # Get the application
    application = Application.query.get_or_404(application_id)

    # Ensure this application belongs to the current user
    if application.user_id != current_user.id:
        # TRANSLATED
        return jsonify({
            'success': False,
            'message': 'الوصول مرفوض'
        }), 403

    # Get documents for this application
    documents = Document.query.filter_by(application_id=application.id).all()

    # Format documents for JSON
    formatted_documents = []
    for doc in documents:
        # Translate status for display
        status_display = doc.status # Keep original if no translation needed yet
        if doc.status == 'Uploaded': status_display = 'تم الرفع'
        # Add other status translations if needed

        formatted_documents.append({
            'id': doc.id,
            'name': doc.name, # Should be Arabic from upload/creation
            'file_path': url_for('static', filename=doc.file_path), # Generate URL
            'status': status_display,
            'uploaded_at': doc.uploaded_at.strftime('%Y-%m-%d %H:%M')
        })

    # Format application data
    # Translate status for display
    status_display_app = application.status
    payment_status_display_app = application.payment_status
    status_map = {
        'Pending Review': 'قيد المراجعة',
        'Documents Approved': 'مقبول مبدئياً', # Changed for consistency
        'Documents Rejected': 'المستندات مرفوضة',
        'Enrolled': 'مسجل',
        'Paid': 'مدفوع',
        'Pending Payment': 'بانتظار الدفع',
        'Pending': 'بانتظار الدفع' # Generic pending often means payment
    }
    status_display_app = status_map.get(application.status, application.status)
    payment_status_display_app = status_map.get(application.payment_status, application.payment_status)


    application_data = {
        'id': application.id,
        'app_id': application.app_id,
        'program': application.program, # Should be Arabic if saved correctly
        'status': status_display_app,
        'payment_status': payment_status_display_app,
        'date': application.date_submitted.strftime('%Y-%m-%d')
    }

    # Get user info for document requirements (Translate nationality if needed)
    nationality_display = current_user.nationality
    if current_user.nationality == 'Egyptian': nationality_display = 'مصري'
    # Add other nationalities if stored differently

    user_info = {
        'nationality': nationality_display,
        'gender': current_user.gender or 'غير محدد'
    }

    return jsonify({
        'success': True,
        'application': application_data,
        'documents': formatted_documents,
        'user_info': user_info
    })

# ...existing code...

# Add this context processor
@app.context_processor
def utility_processor():
    return {
        'now': datetime.now(UTC)
    }

from commands import init_app
init_app(app)

@app.route('/admin/students')
@login_required
def admin_students():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    # Get students with university IDs, eager loading related data
    student_enrollments = db.session.query(User, StudentID, Application).join(
        Application, User.id == Application.user_id
    ).join(
        StudentID, Application.id == StudentID.application_id
    ).options(
        joinedload(User.applications).joinedload(Application.student_id) # Corrected relationship name
    ).order_by(User.full_name).all() # Order by name

    students = []
    for user, student_id_obj, application in student_enrollments:
         students.append({
             'id': user.id,
             'student_id': student_id_obj.student_id,
             'name': user.full_name,
             'program': application.program, # Should be Arabic if saved correctly
             'email': user.email # Add email for easy contact
         })


    return render_template('admin/students.html', students=students)

@app.route('/admin/student/<int:user_id>/courses')
@login_required
def admin_student_courses(user_id):
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))

    # Get student
    student = User.query.get_or_404(user_id)

    # Get student's university ID and application/program info
    student_id_obj = StudentID.query.join(Application).filter(
        Application.user_id == user_id
    ).options(
        joinedload(StudentID.application).joinedload(Application.program_relation) # Eager load application and program
    ).first()

    if not student_id_obj:
        # TRANSLATED flash message
        flash('لم يتم تعيين رقم جامعي لهذا الطالب.', 'warning')
        return redirect(url_for('admin_students'))

    application = student_id_obj.application
    program_name = application.program # Display name from application (should be Arabic)
    program_db = application.program_relation # Actual Program object

    # Initialize courses list
    courses_data = []
    # Translate status map for display
    status_map_display = {
        'Enrolled': 'مسجل',
        'Completed': 'مكتمل',
        'Failed': 'راسب',
        'In Progress': 'قيد الدراسة' # Or another suitable term
    }


    try:
        # --- Fetch ENROLLED courses directly for this student ---
        enrolled_items = db.session.query(
            Course, CourseEnrollment
        ).join(
            CourseEnrollment, Course.id == CourseEnrollment.course_id
        ).filter(
            CourseEnrollment.student_id == user_id
        ).options(
            joinedload(CourseEnrollment.course) # Eager load course details
        ).order_by(
            CourseEnrollment.academic_year.desc(),
            CourseEnrollment.semester, # Assumes Arabic semester name stored
            Course.code
        ).all()

        enrolled_course_ids = set()
        for course, enrollment in enrolled_items:
            courses_data.append({
                'course': course,
                'semester': enrollment.semester, # Use semester from enrollment (should be Arabic)
                # Translate enrollment status for display
                'enrollment_status': status_map_display.get(enrollment.status, enrollment.status),
                'grade': enrollment.grade, # Letter grade (A+, B, etc.)
                'grade_numeric': enrollment.grade_numeric, # Numeric grade (0-100)
                'enrollment_id': enrollment.id
            })
            enrolled_course_ids.add(course.id)

    except Exception as e:
        app.logger.error(f"Error fetching courses for student {user_id} in admin view: {str(e)}", exc_info=True)
        # TRANSLATED flash message
        flash('خطأ في تحميل بيانات المقررات للطالب.', 'danger')
        # Continue with potentially empty list

    return render_template('admin/student_courses.html',
                         student=student,
                         student_id=student_id_obj.student_id,
                         program=program_name,
                         courses=courses_data) # Pass the unified list

@app.route('/admin/update_grade', methods=['POST'])
@login_required
def admin_update_grade():
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'})

    enrollment_id = request.form.get('enrollment_id')
    grade_str = request.form.get('grade')

    if not enrollment_id or grade_str is None:
        # TRANSLATED
        return jsonify({'success': False, 'message': 'البيانات المطلوبة غير متوفرة (معرف التسجيل والدرجة)'})

    try:
        enrollment = CourseEnrollment.query.options(
            joinedload(CourseEnrollment.student),
            joinedload(CourseEnrollment.course)
        ).get_or_404(int(enrollment_id))
        
        student = enrollment.student
        course = enrollment.course

        try:
            numerical_grade = int(float(grade_str))
        except ValueError:
             return jsonify({'success': False, 'message': 'الدرجة يجب أن تكون رقماً.'})

        if numerical_grade < 0: numerical_grade = 0
        elif numerical_grade > 100: numerical_grade = 100

        letter_grade = 'F'
        if numerical_grade >= 95: letter_grade = 'A+'
        elif numerical_grade >= 90: letter_grade = 'A'
        elif numerical_grade >= 85: letter_grade = 'A-'
        elif numerical_grade >= 80: letter_grade = 'B+'
        elif numerical_grade >= 75: letter_grade = 'B'
        elif numerical_grade >= 70: letter_grade = 'B-'
        elif numerical_grade >= 65: letter_grade = 'C+'
        elif numerical_grade >= 60: letter_grade = 'C'
        elif numerical_grade >= 55: letter_grade = 'C-'
        elif numerical_grade >= 50: letter_grade = 'D+'
        elif numerical_grade >= 45: letter_grade = 'D'

        gpa_map = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
        }

        enrollment.grade = letter_grade
        enrollment.grade_numeric = numerical_grade
        enrollment.gpa_value = gpa_map.get(letter_grade, 0.0)

        # TRANSLATED statuses
        enrollment.status = 'راسب' if numerical_grade < 45 else 'مكتمل'
        
        # --- NOTIFICATION & EMAIL (In-app part) ---
        notification = Notification(
            user_id=student.id,
            message=f'تم رصد درجتك في مقرر {course.code} - {course.title}.',
            url=url_for('student_courses')
        )
        db.session.add(notification)
        db.session.commit()

        # --- NOTIFICATION & EMAIL (Email part) ---
        email_subject = f"تم رصد درجتك في مقرر {course.code}"
        email_body_html = f"""
        <html dir="rtl" lang="ar">
        <head><meta charset="UTF-8"></head>
        <body>
            <p>مرحباً {student.full_name},</p>
            <p>تم رصد درجتك النهائية في المقرر التالي:</p>
            <ul>
                <li><strong>رمز المقرر:</strong> {course.code}</li>
                <li><strong>اسم المقرر:</strong> {course.title}</li>
                <li><strong>الدرجة النهائية:</strong> {numerical_grade}%</li>
                <li><strong>التقدير:</strong> {letter_grade}</li>
            </ul>
            <p>يمكنك الاطلاع على جميع درجاتك من خلال صفحة المقررات الدراسية في حسابك.</p>
            <p style="text-align: center;">
                <a href="{url_for('student_courses', _external=True)}" style="background-color: #17a2b8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    عرض المقررات الدراسية
                </a>
            </p>
            <hr>
            <p>فريق الدراسات العليا</p>
        </body>
        </html>
        """
        send_email(student.email, email_subject, email_body_html)
        
        return jsonify({'success': True, 'message': f'تم تحديث الدرجة إلى {letter_grade} ({numerical_grade}%) بنجاح.'})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating grade for enrollment {enrollment_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'حدث خطأ أثناء تحديث الدرجة: {str(e)}'})


@app.route('/api/program-info')
def api_program_info():
    degree_type = request.args.get('degree') # e.g., Diploma, Master, PhD
    program_name = request.args.get('name') # Could be English or Arabic name from dropdown

    app.logger.info(f"API Request - /api/program-info - degree: '{degree_type}', program_name: '{program_name}'")

    if not degree_type or not program_name:
        app.logger.warning("Missing parameters in /api/program-info request")
        # TRANSLATED
        return jsonify({'success': False, 'message': 'المعاملات المطلوبة (degree, name) مفقودة'})

    # Try to find the program using multiple strategies (prioritize Arabic name match if provided)
    program = None
    search_strategies = [
        # Check if program_name exactly matches an Arabic name
        ("Arabic name exact match", lambda: Program.query.filter_by(arabic_name=program_name, degree_type=degree_type).first()),
        # Check if program_name exactly matches an English name
        ("English name exact match", lambda: Program.query.filter_by(name=program_name, degree_type=degree_type).first()),
        # Case-insensitive Arabic name match
        ("Arabic name case-insensitive match", lambda: Program.query.filter(Program.arabic_name.ilike(f"{program_name}"), Program.degree_type==degree_type).first()),
        # Case-insensitive English name match
        ("English name case-insensitive match", lambda: Program.query.filter(Program.name.ilike(f"{program_name}"), Program.degree_type==degree_type).first()),
    ]

    for strategy_name, search_func in search_strategies:
        program = search_func()
        if program:
            app.logger.info(f"Found program using strategy '{strategy_name}': ID={program.id}, Name={program.name}, ArabicName={program.arabic_name}, Degree={program.degree_type}")
            break

    # Handle potential variations if still not found (less likely if dropdown uses exact names)
    if not program:
        app.logger.warning(f"Program not found for degree_type='{degree_type}', name='{program_name}' after standard strategies.")
        # Optionally try fuzzy matching or suggest similar ones
        similar_programs = Program.query.filter(
             Program.degree_type==degree_type
         ).limit(5).all()
        # Suggest Arabic names if available, otherwise English
        suggestions = [(p.arabic_name if p.arabic_name else p.name) for p in similar_programs]
        # TRANSLATED response
        return jsonify({
            'success': False,
            'message': 'لم يتم العثور على البرنامج المحدد.',
            'suggestions': suggestions,
            'recommendation': 'تأكد من اختيار البرنامج الصحيح من القائمة أو تحقق من بيانات البرنامج في قاعدة البيانات.'
        })

    # Found the program, now get its courses
    app.logger.info(f"Processing found program: ID={program.id}, Name={program.name}, ArabicName={program.arabic_name}")

    # Get courses for program using ProgramCourse mapping
    semester1_courses = []
    semester2_courses = []
    total_credits = 0

    # Query ProgramCourse joined with Course
    program_course_items = db.session.query(
        Course, ProgramCourse.semester
    ).join(
        ProgramCourse, Course.id == ProgramCourse.course_id
    ).filter(
        ProgramCourse.program_id == program.id,
        Course.is_active == True # Only include active courses
    ).order_by(
        ProgramCourse.semester, Course.code # Order by semester then code
    ).all()

    app.logger.info(f"Found {len(program_course_items)} active course associations for program ID {program.id}")

    for course, semester_num in program_course_items:
         course_data = {
             'id': course.id,
             'code': course.code,
             'title': course.title, # Keep English title for now, consider adding arabic_title to Course model
             'credits': course.credits
         }
         if semester_num == 1:
             semester1_courses.append(course_data)
         elif semester_num == 2:
             semester2_courses.append(course_data)
         else:
              app.logger.warning(f"Course association found with invalid semester number ({semester_num}) for program ID {program.id}, course ID {course.id}")

         total_credits += course.credits

    app.logger.info(f"Program {program.id}: Semester 1 courses: {len(semester1_courses)}, Semester 2 courses: {len(semester2_courses)}, Total Credits: {total_credits}")

    if not program_course_items:
        app.logger.warning(f"No active courses found linked via ProgramCourse for program {program.name} ({program.degree_type}). Check ProgramCourse data and course statuses.")


    response_data = {
        'success': True,
        'program': {
            'id': program.id,
            'name': program.name, # English name
            'degree_type': program.degree_type,
            'description': program.description, # English description
            'arabic_name': program.arabic_name, # Arabic name
            'arabic_description': program.arabic_description, # Arabic description
            'semester1_courses': semester1_courses,
            'semester2_courses': semester2_courses,
            'total_credits': total_credits
        }
    }
    app.logger.info(f"Returning program info response for program ID {program.id}")

    return jsonify(response_data)

# ...existing code...

@app.route('/api/programs')
def api_programs():
    """Return available programs as JSON, optionally filtered by degree_type"""
    try:
        # Get filters from query parameters
        degree_filter = request.args.get('degree_type') # e.g., Diploma, Master, PhD
        # program_type_filter = request.args.get('type') # Not currently used for filtering here

        app.logger.debug(f"API Request - /api/programs - degree_type='{degree_filter}'")

        # Start with a base query for active programs
        query = Program.query.filter_by(is_active=True) # Only return active programs

        # Apply degree filter if provided
        if degree_filter:
            query = query.filter(Program.degree_type == degree_filter)
        # Add type filter if needed later
        # if program_type_filter:
        #     if hasattr(Program, 'type'):
        #         query = query.filter(Program.type.ilike(f"%{program_type_filter}%"))

        # Order programs (e.g., by Arabic name if available, then English name)
        all_programs = query.order_by(Program.arabic_name, Program.name).all()

        # Prepare the list for JSON, prioritize Arabic name for display value
        programs_list = []
        for program in all_programs:
             programs_list.append({
                 'id': program.id,
                 'name': program.name, # Keep English name as identifier if needed
                 'degree_type': program.degree_type,
                 'arabic_name': program.arabic_name,
                 # Value for dropdown: Use Arabic name, fallback to English
                 'display_name': program.arabic_name if program.arabic_name else program.name
                 # 'type': program.type if hasattr(program, 'type') else None
             })

        app.logger.info(f"Returning {len(programs_list)} active programs (Degree Type Filter: {degree_filter}).")
        return jsonify({
            'success': True,
            'programs': programs_list
        })
    except Exception as e:
        app.logger.error(f"Error fetching programs API: {str(e)}", exc_info=True)
        # TRANSLATED error response
        return jsonify({
            'success': False,
            'message': f'خطأ في جلب البرامج: {str(e)}'
        }), 500



# --- RE-IMPLEMENTED PDF ANALYSIS ENDPOINT ---
@app.route('/admin/analyze_transcript_pdf', methods=['POST'])
@login_required
def admin_analyze_transcript_pdf():
    """
    Reads a PDF file specified by path, sends the entire encoded file
    to Gemini for analysis against prerequisites, and returns the analysis text.
    This implementation mirrors the more robust logic from your old file.
    """
    start_time = time.time()
    app.logger.info("Received request for /admin/analyze_transcript_pdf")

    if not current_user.is_admin():
        app.logger.warning("Access denied for non-admin user.")
        return jsonify({'success': False, 'message': 'الوصول مرفوض'}), 403

    # --- Get data from request ---
    try:
        data = request.get_json()
        if not data:
            raise ValueError("No JSON data received.")
        # Expecting relative path like 'uploads/user_1_timestamp_transcript.pdf'
        relative_doc_path = data.get('document_path')
        application_id = data.get('application_id') # Optional, for logging

        if not relative_doc_path:
            raise ValueError("Missing 'document_path' in request.")

        app.logger.info(f"Analysis requested for doc path: {relative_doc_path}, app_id: {application_id}")

    except Exception as e:
        app.logger.error(f"Error parsing request data: {str(e)}")
        return jsonify({'success': False, 'message': f'بيانات الطلب غير صالحة: {str(e)}'}), 400

    # --- Construct full file path and check existence ---
    # The path from JS is like 'uploads/filename.pdf', we need to get the filename relative to UPLOAD_FOLDER
    filename_part = os.path.basename(relative_doc_path)

    # Construct the full, absolute path
    full_file_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename_part))

    app.logger.info(f"Attempting to read PDF from absolute path: {full_file_path}")

    if not os.path.exists(full_file_path):
        app.logger.error(f"PDF file not found at path: {full_file_path}")
        return jsonify({'success': False, 'message': 'ملف PDF لكشف الدرجات غير موجود على الخادم.'}), 404

    # --- Read and Base64 Encode PDF ---
    try:
        with open(full_file_path, "rb") as pdf_file:
            pdf_content_bytes = pdf_file.read()
        pdf_base64 = base64.b64encode(pdf_content_bytes).decode('utf-8')
        app.logger.info(f"Successfully read and base64 encoded PDF: {len(pdf_base64)} chars")
    except Exception as e:
        app.logger.error(f"Error reading or encoding PDF file: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'خطأ في معالجة ملف PDF: {str(e)}'}), 500

    # --- Prepare Prompt and Gemini API Call ---
    gemini_api_key = current_app.config.get('GEMINI_API_KEY') or os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key or gemini_api_key == "YOUR_FALLBACK_API_KEY_HERE":
         app.logger.error("Gemini API Key is not configured in app.config or environment variables.")
         return jsonify({'success': False, 'message': 'خدمة التحليل بالذكاء الاصطناعي غير مهيأة.'}), 500
    else:
         app.logger.info("Using Gemini API Key.")

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={gemini_api_key}"

    # Prerequisite courses text (as provided in the old file)
    prerequisite_courses_text = """
SE101: مبادىء نظم الحاسب والبرمجه (Computer Systems Principles and Programming)

المواضيع: البرمجة بلغة C، المؤشرات وإدارة الذاكرة، هياكل البيانات الأساسية، مفاهيم لغة التجميع.

SE102: نظم قواعد البيانات العلاقية (Relational Database Systems)

المواضيع: نمذجة البيانات (ER Model)، نموذج البيانات العلائقي والقيود، تصميم قواعد البيانات (ER/EER to Relational Mapping)، لغة الاستعلامات البنيوية (Basic & Advanced SQL).

SE103: عملية تطوير البرمجيات (The Software Development Process)

المواضيع: دورة حياة تطوير البرمجيات (SDLC)، منهجيات التطوير (الشلال، التكرارية)، هندسة المتطلبات، مبادئ تصميم البرمجيات.

SE104: تصميم بينية المستخدم (The User Interface Design)

المواضيع: مبادئ تصميم الواجهات (UI/UX)، نماذج الاستخدام (Wireframing)، التصميم المرتكز على المستخدم، تقييم قابلية الاستخدام.

SE105: تطوير البرمجيات شيئية التوجه باستخدام UML (Object-Oriented Software Development using UML)

المواضيع: مفاهيم البرمجة الشيئية، مخططات UML، أنماط التصميم (Design Patterns)، مبادئ SOLID.

SE106: إدارة مشروعات البرمجيات (Software Project Management)

المواضيع: تخطيط وجدولة المشاريع، إدارة المخاطر وتقدير التكاليف، منهجيات الإدارة الرشيقة، إدارة الفرق.

SE107: تصميم مواقع الويب (Web Design and Architecture)

المواضيع: HTML, CSS, JavaScript، معمارية العميل والخادم، بروتوكول HTTP، تقنيات الواجهة الخلفية (Backend).

SE108: التطوير الرشيق للبرمجيات (Agile Software Development)

المواضيع: مقدمة في Agile ومبادئه، منهجية Scrum، منهجيات DSDM و FDD، اختبار البرمجيات، تقدير الجهد في Agile.

SE109: البرمجه في الأنظمة الكبيرة (Programming in the Large)

المواضيع: مقدمة في البرمجة الشيئية (OOP)، ميزات OOP، مقدمة في لغة Java، أساسيات Java، تعريف الأصناف والتحكم في الوصول.

"""

    # Construct the translated prompt for analyzing a PDF file
    prompt_text = f"""
أنت مساعد مستشار أكاديمي مفيد لبرامج الدراسات العليا بجامعة القاهرة. مرفق ملف PDF يحتوي على كشف الدرجات الأكاديمي للطالب.

مهمتك هي تحليل محتوى كشف الدرجات هذا ومقارنته بمتطلباتنا الأساسية لتحديد ما إذا كانت هناك حاجة إلى مقررات تكميلية لبرنامج الدراسات العليا في هندسة البرمجيات.

فيما يلي المقررات الأساسية المطلوبة:
{{ {prerequisite_courses_text} }}

يرجى إجراء التحليل التالي بناءً فقط على المحتوى الموجود داخل ملف PDF المقدم:

1.  **تحديد المقررات:** قم بسرد جميع المقررات *المكتملة* المذكورة في ملف PDF الخاص بكشف الدرجات، بما في ذلك رموز وأسماء المقررات إن وجدت.
2.  **التحقق من المتطلبات:** قارن المقررات المكتملة المحددة بقائمة المتطلبات الأساسية (SE101 إلى SE110). اذكر بوضوح أي المتطلبات تبدو مستوفاة بناءً على محتوى كشف الدرجات. استخدم رموز المقررات للمطابقة حيثما أمكن.
3.  **المتطلبات المفقودة:** اذكر صراحةً أي مقررات أساسية (SE101 إلى SE110) *لم يتم العثور عليها* كمقررات مكتملة في ملف PDF الخاص بكشف الدرجات.
4.  **الخلاصة:** قدم ملخصًا موجزًا وواضحًا يوضح ما إذا كان الطالب يبدو مستوفيًا لجميع المتطلبات بناءً *فقط* على ملف PDF هذا، أو إذا كانت هناك متطلبات تبدو مفقودة.

**تعليمات تنسيق هامة:**
*   استخدم Markdown للتنسيق.
*   استخدم عناوين واضحة (مثل  'المقررات المحددة`، ' حالة المتطلبات`،  'المتطلبات المفقودة`، 'الخلاصة`).
*   استخدم نقاط التعداد (`* ` أو `- `).
*   كن موجزًا وركز *فقط* على التحليل المطلوب بناءً على ملف PDF. لا تضف تحيات أو اعتذارات أو حشوًا محادثيًا.
"""

    request_payload = {
        "contents": [
            { "parts": [
                {"text": prompt_text},
                {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}
            ]}
        ],
        "generationConfig": { "temperature": 0.3, "maxOutputTokens": 4096 },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]
    }

    headers = {'Content-Type': 'application/json'}

    # --- Make the API Call ---
    try:
        api_call_start = time.time()
        response = requests.post(gemini_url, headers=headers, json=request_payload, timeout=180) # Increased timeout
        api_call_end = time.time()
        app.logger.info(f"Gemini API call took {api_call_end - api_call_start:.2f} seconds. Status: {response.status_code}")
        response.raise_for_status()
        response_data = response.json()

        analysis_text = response_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')

        if not analysis_text:
             app.logger.warning(f"Gemini response received but text part is empty. Response: {response_data}")
             raise ValueError("أعادت خدمة التحليل نتيجة فارغة.")

        app.logger.info("Successfully received analysis from Gemini.")
        end_time = time.time()
        app.logger.info(f"Total analysis request processed in {end_time - start_time:.2f} seconds.")

        return jsonify({'success': True, 'analysis_text': analysis_text.strip()})

    except requests.exceptions.HTTPError as e:
        error_message = f"AI service returned an error: {e}"
        try:
            error_details = response.json().get('error', {})
            gemini_error = error_details.get('message', str(e))
            error_message = f"خطأ في خدمة الذكاء الاصطناعي: {gemini_error}"
            app.logger.error(f"Gemini API HTTP Error Details: {error_details}")
        except Exception:
            app.logger.error(f"Gemini API HTTP Error (non-JSON): {response.text}")
        return jsonify({'success': False, 'message': error_message}), response.status_code

    except Exception as e:
        app.logger.error(f"Unexpected error during AI analysis: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'حدث خطأ غير متوقع: {str(e)}'}), 500

@app.route('/admin/application/<int:application_id>/details', methods=['GET'])
@login_required
def admin_application_details(application_id):
    """Return application details and documents for admin view"""
    app.logger.debug(f"Accessing admin_application_details for ID: {application_id} with method: {request.method}")
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'}), 403

    try:
        # Get the application, eager load user
        application = Application.query.options(joinedload(Application.user)).get_or_404(application_id)

        # Get documents for this application
        documents = Document.query.filter_by(application_id=application.id).all()

        # Format documents for JSON
        formatted_documents = []
        for doc in documents:
             # Translate status for display
             status_display = doc.status
             if doc.status == 'Uploaded': status_display = 'تم الرفع'
             # Add other statuses if needed
             elif doc.status == 'Approved': status_display = 'مقبول'
             elif doc.status == 'Rejected': status_display = 'مرفوض'

             formatted_documents.append({
                 'id': doc.id,
                 'name': doc.name, # Should be Arabic
                 'file_path': url_for('static', filename=doc.file_path), # URL for viewing/downloading
                 'status': status_display,
                 'uploaded_at': doc.uploaded_at.strftime('%Y-%m-%d %H:%M')
             })

        # Format application data with user information
        user = application.user # Already loaded
        # Translate statuses
        status_map = {
            'Pending Review': 'قيد المراجعة',
            'Documents Approved': 'مقبول مبدئياً',
            'Documents Rejected': 'المستندات مرفوضة',
            'Enrolled': 'مسجل',
            'Paid': 'مدفوع',
            'Pending Payment': 'بانتظار الدفع',
            'Pending': 'بانتظار الدفع'
        }
        app_status_display = status_map.get(application.status, application.status)
        payment_status_display = status_map.get(application.payment_status, application.payment_status)

        application_data = {
            'id': application.id,
            'app_id': application.app_id,
            'applicant': user.full_name,
            'email': user.email,
            # TRANSLATED 'Not provided'
            'phone': user.phone or 'غير متوفر',
            'program': application.program, # Should be Arabic
            'status': app_status_display,
            'payment_status': payment_status_display,
            'date': application.date_submitted.strftime('%Y-%m-%d')
        }

        return jsonify({
            'success': True,
            'application': application_data,
            'documents': formatted_documents
        })
    except Exception as e:
        app.logger.error(f"Error retrieving application details for ID {application_id}: {str(e)}", exc_info=True)
        # TRANSLATED error message
        return jsonify({
            'success': False,
            'message': f'خطأ في استرجاع تفاصيل الطلب: {str(e)}'
        }), 500

@app.route('/admin/send_message', methods=['POST'])
@login_required
def admin_send_message():
    """Handles sending a message from admin to a student, creating a ticket."""
    if not current_user.is_admin():
        # TRANSLATED
        return jsonify({'success': False, 'message': 'الوصول مرفوض'}), 403

    try:
        data = request.get_json()
        student_id = data.get('user_id')
        subject = data.get('subject')
        message_text = data.get('message')

        if not student_id or not subject or not message_text:
            # TRANSLATED
            return jsonify({'success': False, 'message': 'معرف الطالب والموضوع والرسالة حقول مطلوبة.'}), 400

        student = User.query.get(student_id)
        if not student or student.role != 'student':
            # TRANSLATED
            return jsonify({'success': False, 'message': 'لم يتم العثور على الطالب أو المستخدم ليس طالبًا.'}), 404

        # Generate a unique ticket ID
        ticket_count = Ticket.query.count() + 1
        ticket_id_str = f"TKT-{ticket_count:04d}" # Use 4 digits for padding

        # Create new ticket
        new_ticket = Ticket(
            ticket_id=ticket_id_str,
            user_id=student.id,
            subject=subject,
            # TRANSLATED status
            status='مفتوحة', # Start as Open
            created_at=datetime.now(UTC)
        )
        db.session.add(new_ticket)
        db.session.flush() # Get the ID before committing

        # Add the message from the admin
        admin_message = TicketMessage(
            ticket_id=new_ticket.id,
            sender='Admin', # Keep as Admin
            message=message_text,
            created_at=datetime.now(UTC)
        )
        db.session.add(admin_message)

        # Create notification for the student
        # TRANSLATED notification message
        notification = Notification(
            user_id=student.id,
            message=f'رسالة جديدة من الإدارة بخصوص: {subject}',
            read=False,
            created_at=datetime.now(UTC),
            url=url_for('student_ticket_detail', ticket_id=new_ticket.id)
        )
        db.session.add(notification)

        db.session.commit()
        app.logger.info(f"Admin {current_user.id} sent message creating ticket {ticket_id_str} for student {student_id}")
        
        # --- NOTIFICATION & EMAIL ---
        email_body_html = f"""
        <html dir="rtl" lang="ar">
        <head><meta charset="UTF-8"></head>
        <body>
            <p>مرحباً {student.full_name},</p>
            <p>لديك رسالة جديدة من الإدارة بخصوص "{subject}".</p>
            <p>لعرض الرسالة والرد عليها، يرجى زيارة قسم الدعم الفني في حسابك.</p>
            <p style="text-align: center;">
                <a href="{url_for('student_ticket_detail', ticket_id=new_ticket.id, _external=True)}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    عرض الرسالة
                </a>
            </p>
            <hr>
            <p>فريق الدراسات العليا</p>
        </body>
        </html>
        """
        send_email(student.email, f"رسالة جديدة من الإدارة: {subject}", email_body_html)

        # TRANSLATED success message
        return jsonify({'success': True, 'message': 'تم إرسال الرسالة وإنشاء تذكرة دعم جديدة.'})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error sending message from admin: {str(e)}", exc_info=True)
        # TRANSLATED error message
        return jsonify({'success': False, 'message': f'حدث خطأ داخلي أثناء إرسال الرسالة: {str(e)}'}), 500


if __name__ == '__main__':
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Check and add missing columns (using raw SQL for SQLite compatibility)
        try:
            # TRANSLATED print message
            print("التحقق من الأعمدة المفقودة في قاعدة البيانات...")
            inspector = db.inspect(db.engine)
            table_names = inspector.get_table_names()

            def check_and_add_column(table_name, column_name, column_type):
                if table_name in table_names:
                    columns = [col['name'] for col in inspector.get_columns(table_name)]
                    if column_name not in columns:
                        # TRANSLATED print message
                        print(f"إضافة عمود '{column_name}' إلى جدول '{table_name}'...")
                        try:
                            db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
                            db.session.commit()
                            # TRANSLATED print message
                            print(f"تمت إضافة عمود '{column_name}' بنجاح!")
                        except Exception as alter_err:
                             db.session.rollback()
                             # TRANSLATED print message
                             print(f"خطأ أثناء إضافة العمود '{column_name}' إلى '{table_name}': {alter_err}")

            # Check user table for new columns
            check_and_add_column('user', 'gender', 'VARCHAR(10)')
            check_and_add_column('user', 'military_status', 'VARCHAR(20)')
            check_and_add_column('user', 'is_verified', 'BOOLEAN DEFAULT FALSE') # Add verification column

            # Check course_enrollments table
            check_and_add_column('course_enrollments', 'gpa_value', 'FLOAT')
            check_and_add_column('course_enrollments', 'program_id', 'INTEGER REFERENCES programs(id)')
            check_and_add_column('course_enrollments', 'academic_year', 'VARCHAR(20)')
            check_and_add_column('course_enrollments', 'semester', 'VARCHAR(50)') # Store Arabic name
            check_and_add_column('course_enrollments', 'grade_numeric', 'FLOAT')

            # Check programs table
            check_and_add_column('programs', 'arabic_name', 'TEXT')
            check_and_add_column('programs', 'arabic_description', 'TEXT')
            check_and_add_column('programs', 'type', 'VARCHAR(50)') # e.g., Academic, Professional (مهني, أكاديمي)
            check_and_add_column('programs', 'is_active', 'BOOLEAN DEFAULT TRUE') # Add active flag

            # Check application table
            check_and_add_column('application', 'academic_year', 'VARCHAR(20)')
            check_and_add_column('application', 'semester', 'VARCHAR(10)') # Stores '1' or '2'
            check_and_add_column('application', 'program_type', 'VARCHAR(50)') # Stores program type at time of application

            # Check news table
            check_and_add_column('news', 'is_active', 'BOOLEAN DEFAULT TRUE')

            # Check course table
            check_and_add_column('course', 'is_active', 'BOOLEAN DEFAULT TRUE')
            
            # Check notification table for URL
            check_and_add_column('notification', 'url', 'VARCHAR(255)')


        except Exception as e:
            # TRANSLATED print message
            print(f"خطأ أثناء التحقق من / إضافة الأعمدة: {str(e)}")
            traceback.print_exc()
            db.session.rollback()

    app.run(debug=True)
