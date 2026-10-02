import os
import sys
import argparse
from getpass import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def create_admin(full_name: str, email: str, password: str):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User with email {email} already exists.")
            return

        admin = User(
            full_name=full_name,
            email=email,
            hashed_password=get_password_hash(password),
            role="admin"
        )
        db.add(admin)
        db.commit()
        print(f"Successfully created admin user: {email}")
    except Exception as e:
        print(f"Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--name", help="Admin's full name", required=True)
    parser.add_argument("--email", help="Admin's email address", required=True)
    args = parser.parse_args()
    
    password = getpass("Enter password for admin: ")
    create_admin(args.name, args.email, password)
