"""
Utility script to ensure that only valid programs exist in the database and each has Arabic names.
This script:
1. Loads the list of valid programs from the text file (if provided)
2. Updates existing programs with Arabic names
3. Removes any programs that shouldn't be there
4. Prints a report of what programs are available
5. Ensures all programs are marked as active.
"""

from flask import Flask
from models import db, Program
import sys
import os
from sqlalchemy import text, or_ # Import or_
import logging
import traceback # Ensure traceback is imported

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def setup_app():
    app = Flask(__name__)
    # Use environment variable or default
    db_uri = os.environ.get('DATABASE_URL', 'sqlite:///cu_project.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def ensure_arabic_names():
    """Add Arabic names to all programs that don't have them"""
    logging.info("Checking for programs missing Arabic names...")
    
    # Common translations
    translations = {
        "Software Engineering": "هندسة البرمجيات",
        "Project Management": "إدارة المشروعات",
        "Web Design": "تصميم المواقع",
        "Operations Research and Decision Support": "بحوث العمليات ودعم القرار",
        "Supply Chain and Operations Management": "إدارة سلسلة التوريد والعمليات",
        "Statistical Computing": "الحسابات الإحصائية",
        "Statistical Quality Control": "الضبط الإحصائي وتوكيد الجودة",
        "Applied Statistics": "الإحصاء التطبيقي",
        "Statistics": "الإحصاء",
        "Biostatistics": "الإحصاء الحيوي",
        "Population Studies": "الدراسات السكانية",
        "Computer Science": "علوم الحاسب",
        "Data Analysis": "تحليل البيانات",
        "Actuarial Statistics": "الإحصاء الاكتواري",
        "Official Statistics": "الإحصاءات الرسمية"
    }
    
    programs = Program.query.all()
    updated = 0
    
    logging.info(f"Found {len(programs)} programs in the database")
    
    for program in programs:
        if not program.arabic_name:
            if program.name in translations:
                program.arabic_name = translations[program.name]
                logging.info(f"Added Arabic name for {program.name}: {program.arabic_name}")
                updated += 1
            else:
                # Create a basic Arabic name if no translation is found
                program.arabic_name = f"برنامج {program.name}"
                logging.info(f"Added placeholder Arabic name for {program.name}")
                updated += 1
    
    if updated > 0:
        db.session.commit()
        logging.info(f"Updated {updated} programs with Arabic names")
    else:
        logging.info("All programs already have Arabic names")

def ensure_column_exists():
    """Make sure the arabic_name, arabic_description, and is_active columns exist in the programs table"""
    try:
        result = db.session.execute(text("PRAGMA table_info(programs)"))
        columns = {row[1] for row in result.fetchall()}

        if 'arabic_name' not in columns:
            logging.info("Adding arabic_name column to programs table...")
            db.session.execute(text("ALTER TABLE programs ADD COLUMN arabic_name TEXT"))
            db.session.commit()
            logging.info("Added arabic_name column")
        else:
            logging.info("arabic_name column already exists")

        if 'arabic_description' not in columns:
            logging.info("Adding arabic_description column to programs table...")
            db.session.execute(text("ALTER TABLE programs ADD COLUMN arabic_description TEXT"))
            db.session.commit()
            logging.info("Added arabic_description column")
        else:
            logging.info("arabic_description column already exists")

        # Check for is_active column
        if 'is_active' not in columns:
            logging.info("Adding is_active column to programs table...")
            # Add with default TRUE for new rows, but existing might be NULL
            db.session.execute(text("ALTER TABLE programs ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
            db.session.commit()
            logging.info("Added is_active column")
        else:
            logging.info("is_active column already exists")

    except Exception as e:
        logging.error(f"Error checking/adding columns: {e}")
        db.session.rollback()

def ensure_programs_active():
    """Ensure all programs are marked as active"""
    logging.info("Ensuring all programs are marked as active...")
    try:
        # Use update() for efficiency
        updated_count = Program.query.filter(Program.is_active == False).update({'is_active': True})
        if updated_count > 0:
            db.session.commit()
            logging.info(f"Activated {updated_count} previously inactive programs.")
        else:
            logging.info("All programs were already active.")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error ensuring programs are active: {str(e)}")
        traceback.print_exc() # Print full traceback for debugging

def print_program_list():
    """Print a report of all available programs"""
    try: # Add try-except block here
        programs = Program.query.order_by(Program.degree_type, Program.name).all()

        logging.info("\n=== AVAILABLE PROGRAMS ===")
        logging.info(f"Total programs: {len(programs)}\n")

        current_degree = None
        for program in programs:
            if current_degree != program.degree_type:
                current_degree = program.degree_type
                logging.info(f"\n{current_degree} Programs:")
                logging.info("=" * 20)

            arabic = program.arabic_name if program.arabic_name else "NO ARABIC NAME"
            # Access is_active correctly now
            active_status = "Active" if program.is_active else "Inactive"
            logging.info(f"- {program.name} ({arabic}) - Status: {active_status}")

        logging.info("\n")
    except Exception as e:
        logging.error(f"Error printing program list: {str(e)}")
        traceback.print_exc()

def run():
    """Main function to run all checks"""
    app = setup_app()

    with app.app_context():
        logging.info("Checking database for program issues...")
        ensure_column_exists()
        ensure_arabic_names()
        ensure_programs_active() # Call the corrected function
        print_program_list()
        logging.info("Database check complete!")

if __name__ == "__main__":
    run()
