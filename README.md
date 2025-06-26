# Cairo-University-Portal

https://www.cu-platform.com/

# University Portal: Comprehensive README

This document provides a comprehensive overview of the University Portal, a robust web application designed to streamline academic and administrative processes for students and administrators within a university environment. The platform offers a user-friendly interface for managing applications, documents, courses, support tickets, and various administrative tasks.

## Project Title

University Portal

## Description

The University Portal is a full-stack web application built with Flask, designed to serve as a central hub for higher education institutions. It facilitates student management from application submission to course enrollment and certificate requests, alongside a powerful admin dashboard for oversight and control. The platform supports a multilingual interface (Arabic and English) and integrates with cloud storage for document management and external APIs for advanced functionalities like AI-powered transcript analysis.

## Features

### Student-Facing Features

  * **User Authentication & Profile Management:** Secure registration, login, password reset, email verification, and personal profile updates.
  * **Application Management:** Submit new applications, track application status, and view application details.
  * **Document Management:** Upload, view, and manage required documents for applications and other purposes. Includes support for PDF and image formats, with secure cloud storage (AWS S3 integration).
  * **Certificate Requests:** Request various types of academic certificates (e.g., transcripts, enrollment, completion, graduation), track their status, and manage payments.
  * **Support Ticket System:** Create, view, and reply to support tickets for technical or administrative assistance.
  * **Course Management:** View enrolled courses, track grades and GPA, and enroll in available courses.
  * **Payment Processing:** Simulate payment for application fees and certificate requests.
  * **Personalized Dashboard:** A personalized overview of application status, documents, tickets, and academic progress.

### Admin-Facing Features

  * **Centralized Dashboard:** Overview of new applications, pending payments, open tickets, student statistics (national/international), and top-enrolled courses.
  * **Application Management:** Review, approve, and reject student applications. Send notes to students regarding their applications.
  * **Enrollment & Student ID Generation:** Generate unique student IDs for accepted applicants and manage student enrollments.
  * **Certificate Management:** Track and update the status of certificate requests. Mark certificates as ready for pickup.
  * **Project Repository Management:** Add, edit, delete, and manage academic or research projects displayed on the public portal. Includes image uploads to cloud storage.
  * **News & Announcement Management:** Create, edit, and delete news articles and announcements for the public portal.
  * **Support Ticket System:** View all student support tickets, reply to messages, and update ticket statuses.
  * **User & Course Management:** View registered students, manage their courses, and update grades for enrolled courses.
  * **System Settings:** Basic system settings for fees and notifications.
  * **AI-Powered Transcript Analysis:** Utilize AI (Gemini API) to analyze student academic transcripts for quick insights and prerequisite checks (feature available in admin application details).
  * **Notification System:** Send in-app and email notifications to students for important updates.

## Technologies Used

### Backend

  * **Python**
  * **Flask:** Web framework.
  * **Flask-SQLAlchemy:** ORM for database interactions.
  * **SQLAlchemy:** Core database toolkit.
  * **Flask-Login:** User session management.
  * **Flask-Migrate:** Database migrations with Alembic.
  * **Flask-WTF:** Form validation and CSRF protection.
  * **Werkzeug:** WSGI utility library.
  * **Requests:** HTTP library for external API calls (e.g., Gemini).
  * **Boto3:** AWS SDK for Python, used for Amazon S3 integration (document storage, image hosting).
  * **Mailtrap:** For email sending (simulated or real).
  * **PyMuPDF (fitz):** PDF processing for text extraction (used in AI transcript analysis).
  * **ItsDangerous:** Secure token serialization for email verification and password resets.
  * **SQLite:** Default database for development and local testing. Configurable for PostgreSQL in production.
  * **Gunicorn:** WSGI HTTP Server (for production deployment).

### Frontend

  * **HTML5**
  * **CSS3:** Custom styles and responsive design.
  * **JavaScript:** For dynamic UI, form handling, and API interactions.
  * **Bootstrap 5:** CSS framework for responsive and modern UI components.
  * **Font Awesome:** Icon library.
  * **Toastr.js:** JavaScript library for non-blocking notifications.
  * **SweetAlert2:** Customizable pop-up boxes for alerts and confirmations.

## Project Structure

```
.
├── astral-fate/cu-platform/cu-platform-515ae94536fb98802c89cbd43e6026693d8b678d/
│   ├── admin/                         # Admin blueprint related files
│   ├── api/                           # API blueprint related files
│   ├── app/                           # Core Flask application structure (models.py, __init__.py for factory)
│   ├── auth/                          # Authentication blueprint (login, register, routes)
│   ├── static/                        # Static assets (CSS, JS, images)
│   │   ├── css/                       # Stylesheets (main.css, student-styles.css, rtl.css etc.)
│   │   ├── img/                       # Images
│   │   ├── js/                        # JavaScript files (main.js, notifications.js etc.)
│   ├── templates/                     # Jinja2 HTML templates
│   │   ├── admin/                     # Admin dashboard templates
│   │   ├── student/                   # Student portal templates
│   │   └── (root templates: base.html, index.html, login.html, etc.)
│   ├── build.sh                       # Build script for Vercel deployment
│   ├── commands.py                    # Flask CLI custom commands (e.g., init-db)
│   ├── create_admin_service.sql       # SQL script for creating admin service table
│   ├── debug_form.py                  # Helper for debugging WTForms
│   ├── ensure_programs.py             # Script to ensure program data consistency
│   ├── international-students.js      # JS for international student count (example)
│   ├── main/                          # Main blueprint related files
│   ├── migrations/                    # Alembic migration scripts
│   ├── models.py                      # Database models (User, Application, Program, etc.)
│   ├── pdf_utils.py                   # Utility for PDF text extraction
│   ├── populate_db.py                 # Script to populate initial program and course data
│   ├── README.md                      # This README file
│   ├── requirements.txt               # Python dependencies
│   ├── run.py                         # Main Flask application entry point
│   ├── run_migration.py               # Script to run specific database migrations
│   ├── seed_data.py                   # Script for seeding initial data (potentially redundant with populate_db.py)
│   ├── styles.css                     # Additional CSS file
│   ├── update_db.py                   # Script for updating database schema (potentially redundant with migrations)
│   └── vercel.json                    # Vercel deployment configuration
```

## Setup and Installation

### Prerequisites

  * Python 3.8+
  * pip (Python package installer)
  * Git (for cloning the repository)
  * An AWS S3 bucket and IAM credentials (AWS\_ACCESS\_KEY\_ID, AWS\_SECRET\_ACCESS\_KEY, S3\_BUCKET\_NAME, S3\_REGION) if using S3 for file storage.
  * A Mailtrap API Token if using Mailtrap for email sending.
  * A Google Gemini API Key for AI transcript analysis.

### Local Installation

1.  **Clone the repository:**

    ```bash
    git clone [repository_url]
    cd cairo-university-portal
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: `venv\Scripts\activate`
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set environment variables:**
    Create a `.env` file in the root directory and add the following (replace placeholders with your actual values):

    ```env
    SECRET_KEY='your_super_secret_key_here_for_flask_sessions_and_tokens'
    DATABASE_URL='sqlite:///cu_project.db' # Or your PostgreSQL connection string
    # For S3 (if enabled)
    AWS_ACCESS_KEY_ID='YOUR_AWS_ACCESS_KEY_ID'
    AWS_SECRET_ACCESS_KEY='YOUR_AWS_SECRET_ACCESS_KEY'
    S3_BUCKET_NAME='your-s3-bucket-name'
    S3_REGION='your-s3-bucket-region' # e.g., us-east-1, eu-north-1
    # For Mailtrap (if enabled)
    MAILTRAP_API_TOKEN='YOUR_MAILTRAP_API_TOKEN'
    MAIL_DEFAULT_SENDER='noreply@yourdomain.com'
    # For Google Gemini API (if enabled for AI analysis)
    GEMINI_API_KEY='YOUR_GOOGLE_GEMINI_API_KEY'
    ```

5.  **Initialize the database:**
    This will create the `cu_project.db` file (for SQLite) and set up the initial schema, including an admin user.

    ```bash
    flask --app run init-db
    ```

      * **Admin Credentials:**
          * Email: `admin@example.com`
          * Password: `adminpassword`

6.  **Populate initial program data (optional but recommended):**
    This script adds predefined academic programs and courses to the database.

    ```bash
    python3 populate_db.py
    ```

### Running the Application

1.  **Start the Flask development server:**
    ```bash
    flask --app run run --debug
    ```
    The application will typically run on `http://127.0.0.1:5000/`.

## Usage

  * **Public Website:** Navigate to the root URL (`/`) to access the public-facing university portal, including programs, projects, news, and announcements.
  * **Student Portal:** Register a new student account via `/register` or login via `/login`.
  * **Admin Portal:** Log in with admin credentials via `/login`.

## Deployment

This project is configured for deployment on [Vercel](https://vercel.com/) using the `vercel.json` file. Ensure all environment variables (especially `SECRET_KEY`, `DATABASE_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`, `S3_REGION`, `MAILTRAP_API_TOKEN`, `GEMINI_API_KEY`) are set up correctly in your Vercel project settings. The `build.sh` script handles initial database population on deployment.

## Contributing



| STUDENT NAME                       | ID        |
| :--------------------------------- | :-------- |
| أحمد كرم محمد محمود طلعت          | 202401665 |
| ابراهيم سعودي ابراهيم محمد          | 202301552 |
| عبد الرحمن علي محمد جمال          | 202402483 |
| فاطمة محمد عماد الدين              | 202401205 |
| هاني محمد سيد علي                 | 202402522 |
| هنوف أمين سالم الظلال              | 202403049 |

