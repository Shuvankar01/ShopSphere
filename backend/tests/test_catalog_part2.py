"""Part 2 tests: category hierarchy/cycles, brands, specifications, SKU
conflicts, related products, variant stock linkage, and search filters."""


class TestCategoryHierarchy:
    def test_category_cycle_prevented(self, client, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        parent = client.post("/api/categories", json={"name": "CycleParent"}, headers=h).json()
        child = client.post(
            "/api/categories", json={"name": "CycleChild", "parent_id": parent["id"]}, headers=h
        ).json()

        # Moving a parent under its own descendant creates a cycle.
        r = client.put(f"/api/categories/{parent['id']}", json={"parent_id": child["id"]}, headers=h)
        assert r.status_code == 400
        assert "descendant" in r.json()["detail"].lower()

        # A category cannot be its own parent.
        r = client.put(f"/api/categories/{parent['id']}", json={"parent_id": parent["id"]}, headers=h)
        assert r.status_code == 400

        # A valid move still works.
        root2 = client.post("/api/categories", json={"name": "CycleRoot2"}, headers=h).json()
        r = client.put(f"/api/categories/{child['id']}", json={"parent_id": root2["id"]}, headers=h)
        assert r.status_code == 200

    def test_category_update_missing_parent_rejected(self, client, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        cat = client.post("/api/categories", json={"name": "OrphanCat"}, headers=h).json()
        r = client.put(f"/api/categories/{cat['id']}", json={"parent_id": "does-not-exist"}, headers=h)
        assert r.status_code == 404

    def test_category_filter_includes_descendants(self, client, admin_token, seller_token):
        ah = {"Authorization": f"Bearer {admin_token}"}
        sh = {"Authorization": f"Bearer {seller_token}"}
        parent = client.post("/api/categories", json={"name": "FilterParent"}, headers=ah).json()
        child = client.post(
            "/api/categories", json={"name": "FilterChild", "parent_id": parent["id"]}, headers=ah
        ).json()
        other = client.post("/api/categories", json={"name": "FilterOther"}, headers=ah).json()

        r = client.post(
            "/api/products",
            json={"name": "Child Item", "description": "sits under child", "price": "5.00",
                  "stock": 10, "category_id": child["id"]},
            headers=sh,
        )
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        client.post(
            "/api/products",
            json={"name": "Other Item", "description": "unrelated", "price": "6.00",
                  "stock": 10, "category_id": other["id"]},
            headers=sh,
        )

        # Filtering by the parent returns the child's product too.
        r = client.get("/api/products", params={"category": parent["id"], "limit": 50})
        ids = [p["id"] for p in r.json()["items"]]
        assert pid in ids
        assert all(
            client.get(f"/api/products?category={parent['id']}&limit=50").json()["items"]
        )


class TestBrands:
    def test_brand_crud_and_deactivation(self, client, admin_token, seller_token, category):
        ah = {"Authorization": f"Bearer {admin_token}"}
        sh = {"Authorization": f"Bearer {seller_token}"}

        brand = client.post(
            "/api/brands", json={"name": "PartTwoBrand", "description": "brand desc"}, headers=ah
        )
        assert brand.status_code == 201, brand.text
        brand_id = brand.json()["id"]

        # Public list includes it while active.
        public = client.get("/api/brands").json()
        assert any(b["id"] == brand_id for b in public)

        # Associate a product with the brand.
        r = client.post(
            "/api/products",
            json={"name": "Branded Product", "description": "has a brand", "price": "12.50",
                  "stock": 4, "category_id": category["id"], "brand_id": brand_id},
            headers=sh,
        )
        assert r.status_code == 201, r.text
        prod_id = r.json()["id"]

        # Deactivate the brand (admin only).
        r = client.put(f"/api/brands/{brand_id}", json={"is_active": False}, headers=ah)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

        # Hidden from the public brand list…
        public = client.get("/api/brands").json()
        assert not any(b["id"] == brand_id for b in public)

        # …but brand association survives on the product.
        r = client.get(f"/api/products/{prod_id}")
        assert r.json()["brand"]["id"] == brand_id

    def test_brand_update_by_non_admin_forbidden(self, client, seller_token, admin_token):
        ah = {"Authorization": f"Bearer {admin_token}"}
        brand = client.post("/api/brands", json={"name": "LockedBrand"}, headers=ah).json()
        r = client.put(f"/api/brands/{brand['id']}", json={"description": "nope"},
                       headers={"Authorization": f"Bearer {seller_token}"})
        assert r.status_code == 403


class TestProductCatalogExtras:
    def test_specifications_roundtrip(self, client, seller_token, category):
        h = {"Authorization": f"Bearer {seller_token}"}
        specs = '{"Color": "Black", "Weight": "1.2kg"}'
        r = client.post(
            "/api/products",
            json={"name": "Spec Product", "description": "spec details", "price": "9.99",
                  "stock": 3, "category_id": category["id"], "specifications": specs},
            headers=h,
        )
        assert r.status_code == 201, r.text
        assert r.json()["specifications"] == specs
        pid = r.json()["id"]

        new_specs = '{"Color": "Red"}'
        r = client.put(f"/api/products/{pid}", json={"specifications": new_specs}, headers=h)
        assert r.status_code == 200
        assert r.json()["specifications"] == new_specs

    def test_duplicate_sku_conflict(self, client, seller_token, category):
        h = {"Authorization": f"Bearer {seller_token}"}
        base = {"name": "Sku Product", "description": "sku conflict test", "price": "7.00",
                "stock": 5, "category_id": category["id"], "sku": "DUP-SKU-99"}
        r = client.post("/api/products", json=base, headers=h)
        assert r.status_code == 201, r.text
        r = client.post("/api/products", json={**base, "name": "Sku Product 2"}, headers=h)
        assert r.status_code == 409
        assert "sku" in r.json()["detail"].lower()

    def test_related_products(self, client, seller_token, category):
        h = {"Authorization": f"Bearer {seller_token}"}
        r = client.post(
            "/api/products", json={"name": "Related A", "description": "same category",
                                   "price": "10.00", "stock": 5, "category_id": category["id"]},
            headers=h,
        )
        a = r.json()
        r = client.post(
            "/api/products", json={"name": "Related B", "description": "same category",
                                   "price": "11.00", "stock": 5, "category_id": category["id"]},
            headers=h,
        )
        b = r.json()

        r = client.get(f"/api/products/{a['id']}/related")
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert b["id"] in ids
        assert a["id"] not in ids


class TestVariantStockLinkage:
    def test_stock_derived_from_active_variants(self, client, seller_token, category):
        h = {"Authorization": f"Bearer {seller_token}"}
        r = client.post(
            "/api/products", json={"name": "Variant Product", "description": "variants",
                                   "price": "20.00", "stock": 10, "category_id": category["id"]},
            headers=h,
        )
        pid = r.json()["id"]

        v1 = client.post(
            f"/api/products/{pid}/variants",
            json={"name": "Small", "sku": "VSTOCK-SMALL", "stock": 3},
            headers=h,
        ).json()
        v2 = client.post(
            f"/api/products/{pid}/variants",
            json={"name": "Large", "sku": "VSTOCK-LARGE", "stock": 4},
            headers=h,
        ).json()

        # product.stock mirrors the sum of active variant stocks.
        r = client.get(f"/api/products/{pid}")
        assert r.json()["stock"] == 7

        # Direct product stock edits are blocked while variants exist.
        r = client.put(f"/api/products/{pid}", json={"stock": 99}, headers=h)
        assert r.status_code == 400

        # Deactivating a variant shrinks the derived stock.
        r = client.put(f"/api/products/{pid}/variants/{v1['id']}", json={"is_active": False}, headers=h)
        assert r.status_code == 200
        r = client.get(f"/api/products/{pid}")
        assert r.json()["stock"] == 4

        # Their inventory ledger follows.
        r = client.get(f"/api/inventory/products/{pid}", headers=h)
        assert r.status_code == 200
        assert r.json()["physical_stock"] == 4

        # Updating variant stock works and propagates.
        r = client.put(
            f"/api/products/{pid}/variants/{v2['id']}", json={"stock": 9}, headers=h
        )
        assert r.status_code == 200
        r = client.get(f"/api/products/{pid}")
        assert r.json()["stock"] == 9

    def test_variant_stock_cannot_go_below_reservations(self, client, db, seller_token, category):
        h = {"Authorization": f"Bearer {seller_token}"}
        r = client.post(
            "/api/products", json={"name": "Reserved Product", "description": "variants",
                                   "price": "20.00", "stock": 10, "category_id": category["id"]},
            headers=h,
        )
        pid = r.json()["id"]
        v = client.post(
            f"/api/products/{pid}/variants",
            json={"name": "Only", "sku": "VSTOCK-RESERVED", "stock": 5},
            headers=h,
        ).json()

        from app.models.inventory import Inventory
        inv = db.query(Inventory).filter(Inventory.product_id == pid).one()
        inv.reserved_stock = 4
        db.commit()

        # total=5 with 4 reserved — shrinking below 4 must be rejected.
        r = client.put(f"/api/products/{pid}/variants/{v['id']}", json={"stock": 3}, headers=h)
        assert r.status_code == 400


class TestSearchFilters:
    def test_filter_by_brand_and_discount(self, client, admin_token, seller_token, category):
        ah = {"Authorization": f"Bearer {admin_token}"}
        sh = {"Authorization": f"Bearer {seller_token}"}
        brand = client.post("/api/brands", json={"name": "FilterBrand"}, headers=ah).json()

        r = client.post(
            "/api/products",
            json={"name": "Discounted", "description": "has discount and brand",
                  "price": "50.00", "discount_price": "40.00", "stock": 8,
                  "category_id": category["id"], "brand_id": brand["id"]},
            headers=sh,
        )
        assert r.status_code == 201, r.text
        pid = r.json()["id"]

        r = client.get("/api/products", params={"brand_id": brand["id"], "has_discount": True})
        ids = [p["id"] for p in r.json()["items"]]
        assert pid in ids

        # No discount → excluded when has_discount=true.
        client.post(
            "/api/products", json={"name": "No Discount", "description": "no discount",
                                   "price": "5.00", "stock": 8, "category_id": category["id"],
                                   "brand_id": brand["id"]},
            headers=sh,
        )
        r = client.get("/api/products", params={"brand_id": brand["id"]})
        assert len(r.json()["items"]) == 2
        r = client.get("/api/products", params={"brand_id": brand["id"], "has_discount": True})
        assert len(r.json()["items"]) == 1

    def test_filter_by_min_rating(self, client, customer_token, category, product):
        r = client.post(
            f"/api/products/{product['id']}/reviews",
            json={"rating": 5, "comment": "great"},
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert r.status_code == 201, r.text

        r = client.get("/api/products", params={"min_rating": 4, "limit": 50})
        ids = [p["id"] for p in r.json()["items"]]
        assert product["id"] in ids

        r = client.get("/api/products", params={"min_rating": 4.8, "limit": 50})
        ids = [p["id"] for p in r.json()["items"]]
        assert product["id"] in ids

    def test_filter_in_stock(self, client, seller_token, category):
        h = {"Authorization": f"Bearer {seller_token}"}
        in_stock = client.post(
            "/api/products", json={"name": "InStock Item", "description": "has stock",
                                   "price": "3.00", "stock": 5, "category_id": category["id"]},
            headers=h,
        ).json()
        out = client.post(
            "/api/products", json={"name": "OutOfStock Item", "description": "no stock",
                                   "price": "4.00", "stock": 0, "category_id": category["id"]},
            headers=h,
        ).json()

        r = client.get("/api/products", params={"in_stock": True, "limit": 50})
        ids = [p["id"] for p in r.json()["items"]]
        assert in_stock["id"] in ids
        assert out["id"] not in ids

    def test_search_matches_sku(self, client, seller_token, category):
        h = {"Authorization": f"Bearer {seller_token}"}
        r = client.post(
            "/api/products", json={"name": "SkuSearchable", "description": "desc",
                                   "price": "2.00", "stock": 2, "category_id": category["id"],
                                   "sku": "UNIQUE-SKU-12345"},
            headers=h,
        )
        pid = r.json()["id"]
        r = client.get("/api/products", params={"q": "UNIQUE-SKU-12345"})
        assert any(p["id"] == pid for p in r.json()["items"])

    def test_pagination_bounds_rejected(self, client):
        assert client.get("/api/products", params={"page": 0}).status_code == 422
        assert client.get("/api/products", params={"limit": 101}).status_code == 422
        assert client.get("/api/products", params={"page": -1}).status_code == 422
