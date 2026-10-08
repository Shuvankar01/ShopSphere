"""Part 2 tests: local product image uploads (validation, storage, ownership)."""
import pytest

from app.core.config import settings


@pytest.fixture()
def upload_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    return tmp_path


def _upload(client, product_id, headers, filename="photo.png", content=b"pngbytes", content_type="image/png"):
    return client.post(
        f"/api/products/{product_id}/images/upload",
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


class TestImageUpload:
    def test_upload_valid_image(self, client, seller_token, product, upload_dir):
        r = _upload(client, product["id"], {"Authorization": f"Bearer {seller_token}"})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["url"].startswith("/uploads/")
        assert body["url"].endswith(".png")
        # File actually landed on disk under the upload directory.
        filename = body["url"].split("/")[-1]
        assert (upload_dir / filename).exists()
        # Product image gallery reflects the new image.
        detail = client.get(f"/api/products/{product['id']}").json()
        assert any(img["url"] == body["url"] for img in detail["images"])

    def test_upload_rejects_non_image_extension(self, client, seller_token, product):
        r = _upload(client, product["id"], {"Authorization": f"Bearer {seller_token}"},
                    filename="virus.exe", content=b"MZ", content_type="application/x-msdownload")
        assert r.status_code == 400
        assert "Unsupported file type" in r.json()["detail"]

    def test_upload_rejects_content_type_mismatch(self, client, seller_token, product):
        r = _upload(client, product["id"], {"Authorization": f"Bearer {seller_token}"},
                    filename="photo.png", content=b"x", content_type="text/plain")
        assert r.status_code == 400

    def test_upload_rejects_path_traversal_filename(self, client, seller_token, product):
        r = _upload(client, product["id"], {"Authorization": f"Bearer {seller_token}"},
                    filename="../../etc/passwd.png", content=b"x", content_type="image/png")
        assert r.status_code == 400

    def test_upload_rejects_oversize_file(self, client, seller_token, product, monkeypatch):
        # Shrink the limit so we don't allocate real megabytes.
        monkeypatch.setattr(settings, "MAX_IMAGE_SIZE_MB", 1)
        # Force re-import isn't needed: image_service imports MAX_SIZE_BYTES at
        # module load, so patch the module constant directly.
        import app.services.image_service as img_svc
        img_svc.MAX_SIZE_BYTES = 1024 * 1024
        r = _upload(client, product["id"], {"Authorization": f"Bearer {seller_token}"},
                    content=b"x" * (1024 * 1024 + 1))
        assert r.status_code == 400
        assert "size limit" in r.json()["detail"]

    def test_upload_requires_ownership(self, client, seller_token, product):
        # A second seller cannot upload to someone else's product.
        r = client.post(
            "/api/auth/register",
            json={"full_name": "Other Seller", "email": "other.seller.p2@test.com",
                  "password": "Password123!", "role": "seller"},
        )
        other = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = _upload(client, product["id"], other)
        assert r.status_code == 403

    def test_upload_requires_auth(self, client, product):
        r = _upload(client, product["id"], {})
        assert r.status_code == 401

    def test_delete_image_removes_from_gallery(self, client, seller_token, product):
        h = {"Authorization": f"Bearer {seller_token}"}
        img = _upload(client, product["id"], h).json()
        r = client.delete(
            f"/api/products/{product['id']}/images/{img['id']}", headers=h
        )
        assert r.status_code == 204
        detail = client.get(f"/api/products/{product['id']}").json()
        assert not any(i["id"] == img["id"] for i in detail["images"])
