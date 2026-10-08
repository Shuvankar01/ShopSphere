"""Part 2 tests: inventory operations, movement history, low-stock views, and
concurrent reservation (oversell protection)."""
import threading
import time
import uuid

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.inventory import Inventory
from app.models.product import Category, Product
from app.models.user import User
from app.repositories.inventory_repo import InventoryRepository


def make_seller_and_product(db_engine):
    """Seed a seller + category + product + inventory row on its own committed
    session so independent sessions/threads can see it."""
    Session = sessionmaker(bind=db_engine)
    sess = Session()
    try:
        user = User(full_name="Inv Seller", email=f"inv.seller.{uuid.uuid4().hex[:8]}@test.com",
                    hashed_password="x", role="seller", is_active=True)
        sess.add(user)
        sess.flush()
        cat = Category(name=f"InvCat-{uuid.uuid4().hex[:8]}", is_active=True)
        sess.add(cat)
        sess.flush()
        product = Product(name="Single Unit", description="only one unit", price=15,
                          stock=1, category_id=cat.id, seller_id=user.id, is_active=True)
        sess.add(product)
        sess.flush()
        inv = Inventory(product_id=product.id, physical_stock=1, reserved_stock=0,
                        low_stock_threshold=2)
        sess.add(inv)
        sess.commit()
        return product.id
    finally:
        sess.close()


class TestConcurrentReservation:
    def test_two_customers_cannot_buy_the_single_unit(self, db_engine):
        product_id = make_seller_and_product(db_engine)
        Session = sessionmaker(bind=db_engine)

        results = {}

        def worker(name):
            sess = Session()
            try:
                repo = InventoryRepository(sess)
                inv = repo.get_by_product(product_id, for_update=True)
                # Both threads reach this point before either commits.
                time.sleep(0.15)
                repo.reserve(inv, 1, reference_type="order")
                sess.commit()
                results[name] = True
            except ValueError:
                sess.rollback()
                results[name] = False
            finally:
                sess.close()

        barrier = threading.Barrier(2, timeout=10)

        def worker_synced(name):
            barrier.wait()
            worker(name)

        threads = [threading.Thread(target=worker_synced, args=(f"t{i}",)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert set(results.values()) == {True, False}, (
            "Exactly one customer should win the last unit, the other must fail"
        )

        # The winning reservation is durable.
        check = Session()
        try:
            inv = check.query(Inventory).filter(Inventory.product_id == product_id).one()
            assert inv.reserved_stock == 1
            assert inv.available_stock == 0
        finally:
            check.close()

    def test_reserve_release_deduct_roundtrip(self, db_engine, db, product):
        inv = db.query(Inventory).filter(Inventory.product_id == product["id"]).one()
        repo = InventoryRepository(db)

        repo.reserve(inv, 10, reference_type="order")
        db.commit()
        assert inv.reserved_stock == 10
        assert inv.available_stock == product["stock"] - 10

        repo.release(inv, 10, reference_type="order")
        db.commit()
        assert inv.reserved_stock == 0

        repo.reserve(inv, 5, reference_type="order")
        db.commit()
        repo.deduct(inv, 5, reference_type="order")
        db.commit()
        assert inv.reserved_stock == 0
        assert inv.physical_stock == product["stock"] - 5

        # Movement history has entries for add/reserve/release/deduct.
        movements = repo.get_movements(inv.id)
        types = [m.movement_type for m in movements]
        assert "reserve" in types
        assert "release" in types
        assert "deduct" in types

    def test_reserve_beyond_available_rejected(self, db_engine, db, product):
        inv = db.query(Inventory).filter(Inventory.product_id == product["id"]).one()
        repo = InventoryRepository(db)
        with pytest.raises(ValueError):
            repo.reserve(inv, product["stock"] + 1)
        db.rollback()


class TestInventoryApi:
    def test_set_stock_and_movements_recorded(self, client, seller_token, product):
        h = {"Authorization": f"Bearer {seller_token}"}
        r = client.put(
            f"/api/inventory/products/{product['id']}",
            json={"physical_stock": 25, "low_stock_threshold": 5},
            headers=h,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["physical_stock"] == 25
        assert body["low_stock_threshold"] == 5
        assert body["available_stock"] == 25
        assert body["is_low_stock"] is False

        r = client.get(
            f"/api/inventory/products/{product['id']}/movements", headers=h
        )
        assert r.status_code == 200
        assert r.json(), "movement history should not be empty"

    def test_mine_lists_only_own_products(self, client, seller_token, product):
        h = {"Authorization": f"Bearer {seller_token}"}
        r = client.get("/api/inventory/mine", headers=h)
        assert r.status_code == 200
        items = r.json()
        assert any(i["product_id"] == product["id"] for i in items)
        # The other seller's catalog appears elsewhere — verify via create.
        other = client.post(
            "/api/auth/register",
            json={"full_name": "Inv Other", "email": "inv.other.p2@test.com",
                  "password": "Password123!", "role": "seller"},
        ).json()["access_token"]
        oh = {"Authorization": f"Bearer {other}"}
        r = client.get("/api/inventory/mine", headers=oh)
        assert r.status_code == 200
        assert not any(i["product_id"] == product["id"] for i in r.json())

    def test_low_stock_surface(self, client, seller_token, category):
        h = {"Authorization": f"Bearer {seller_token}"}
        r = client.post(
            "/api/products", json={"name": "Low Stock Item", "description": "barely any",
                                   "price": "4.00", "stock": 2, "category_id": category["id"]},
            headers=h,
        )
        pid = r.json()["id"]
        r = client.get("/api/inventory/low-stock", headers=h)
        assert r.status_code == 200
        assert any(i["product_id"] == pid for i in r.json())

    def test_customer_forbidden_from_inventory_views(self, client, customer_token, product):
        r = client.get("/api/inventory/mine", headers={"Authorization": f"Bearer {customer_token}"})
        assert r.status_code == 403

    def test_admin_can_adjust_stock(self, client, admin_token, product):
        h = {"Authorization": f"Bearer {admin_token}"}
        r = client.post(
            f"/api/inventory/products/{product['id']}/adjust",
            json={"quantity": 5, "note": "restock"},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["physical_stock"] == product["stock"] + 5

    def test_adjust_below_zero_rejected(self, client, admin_token, product):
        h = {"Authorization": f"Bearer {admin_token}"}
        r = client.post(
            f"/api/inventory/products/{product['id']}/adjust",
            json={"quantity": -999999, "note": "oops"},
            headers=h,
        )
        assert r.status_code == 400
