import os
import sys
import asyncio
from sqlalchemy.orm import Session

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database.connection import engine
from app.database.session import SessionLocal
from app.models.user import User
from app.models.product import Category, Product
from app.core.security import get_password_hash

def seed_db():
    db: Session = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.email == "admin@shopsphere.com").first()
        if not admin:
            admin = User(
                full_name="Admin User",
                email="admin@shopsphere.com",
                hashed_password=get_password_hash("admin123"),
                role="admin"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"Created admin user: {admin.email}")

        # Create some categories
        electronics = db.query(Category).filter(Category.name == "Electronics").first()
        if not electronics:
            electronics = Category(name="Electronics", description="Gadgets and devices")
            db.add(electronics)
            
        clothing = db.query(Category).filter(Category.name == "Clothing").first()
        if not clothing:
            clothing = Category(name="Clothing", description="Apparel and fashion")
            db.add(clothing)
            
        db.commit()
        
        # Create some products
        if not db.query(Product).first():
            product1 = Product(
                name="Smartphone X",
                description="Latest smartphone with advanced features.",
                price=999.99,
                stock=50,
                image_url="https://via.placeholder.com/300",
                category_id=electronics.id,
                seller_id=admin.id
            )
            db.add(product1)
            
            product2 = Product(
                name="Cotton T-Shirt",
                description="Comfortable cotton t-shirt for everyday wear.",
                price=19.99,
                stock=200,
                image_url="https://via.placeholder.com/300",
                category_id=clothing.id,
                seller_id=admin.id
            )
            db.add(product2)
            db.commit()
            print("Created sample products.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting database seeder...")
    seed_db()
    print("Database seeding completed.")
