import os
import sys

from sqlalchemy.orm import Session

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.security import get_password_hash
from app.database.session import SessionLocal
from app.models.coupon import Coupon
from app.models.product import Category, Product
from app.models.role import Role, UserRole
from app.models.user import User

ROLE_DESCRIPTIONS = {
    "customer": "Shop and place orders",
    "seller": "Manage own products and inventory",
    "admin": "Full administrative access",
}


def ensure_role_assignment(db: Session, user: User) -> None:
    """Mirror users.role into the normalized roles/user_roles tables (idempotent)."""
    role = db.query(Role).filter(Role.name == user.role).first()
    if role is None:
        role = Role(name=user.role, description=ROLE_DESCRIPTIONS.get(user.role))
        db.add(role)
        db.flush()
    link = (
        db.query(UserRole)
        .filter(UserRole.user_id == user.id, UserRole.role_id == role.id)
        .first()
    )
    if link is None:
        db.add(UserRole(user_id=user.id, role_id=role.id))


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
        ensure_role_assignment(db, admin)
        db.commit()

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

        # Demo coupon (idempotent): 10% off any order, once per customer.
        if not db.query(Coupon).filter(Coupon.code == "WELCOME10").first():
            db.add(
                Coupon(
                    code="WELCOME10",
                    discount_type="percent",
                    discount_value=10,
                    max_uses=1000,
                    is_active=True,
                )
            )
            db.commit()
            print("Created demo coupon WELCOME10 (10% off).")

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
            db.flush()
            # Inventory rows so sellers/checkout have stock to work with
            from app.repositories.inventory_repo import InventoryRepository
            inv_repo = InventoryRepository(db)
            inv_repo.create_for_product(product1.id, initial_stock=50)
            inv_repo.create_for_product(product2.id, initial_stock=200)
            db.commit()
            print("Created sample products.")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting database seeder...")
    try:
        seed_db()
    except Exception:
        print("Database seeding FAILED.")
        sys.exit(1)
    print("Database seeding completed.")
