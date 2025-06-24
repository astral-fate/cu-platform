from run import app
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# This part will run when the Vercel function is initialized
# This happens during deployment and on cold starts for new requests.
with app.app_context():
    try:
        # Import the function from your script
        from populate_db import populate_database
        
        logging.info("Vercel deployment: Running database population script...")
        populate_database()
        logging.info("Database population script finished.")
        
    except Exception as e:
        logging.error(f"Error during database population on Vercel startup: {e}", exc_info=True)

# The 'app' object is then used by Vercel to handle incoming requests.
