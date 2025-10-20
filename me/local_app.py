# Local testing config for Flask app
import os
from dotenv import load_dotenv
from app import app
from models import db

# Load .env if present
load_dotenv()

# Build a safe absolute path to the database file
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "hacklab.db")

# Ensure the folder exists before using it
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Configure Flask SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

print("Using database path:", app.config["SQLALCHEMY_DATABASE_URI"])

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(debug=False, host="127.0.0.1", port=5000)
