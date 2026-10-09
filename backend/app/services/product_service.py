"""Product service — business logic for catalog, search, variants, images, reviews."""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.models.user import User
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.product import (
    BrandCreate,
    BrandResponse,
    BrandUpdate,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    PaginatedProducts,
    ProductCreate,
    ProductImageCreate,
    ProductImageResponse,
    ProductResponse,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
    ReviewCreate,
    ReviewResponse,
)
from app.services.image_service import ImageStorage


class ProductService:
    def __init__(
        self,
        product_repo: ProductRepository,
        inventory_repo: Optional[InventoryRepository] = None,
        image_storage: Optional[ImageStorage] = None,
        order_repo: Optional[OrderRepository] = None,
    ):
        self.product_repo = product_repo
        self.inventory_repo = inventory_repo
        self.image_storage = image_storage or ImageStorage()
        self.order_repo = order_repo

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    def get_categories(self) -> List[CategoryResponse]:
        cats = self.product_repo.get_categories()
        return [CategoryResponse.model_validate(c) for c in cats]

    def create_category(self, data: CategoryCreate, current_user: User) -> CategoryResponse:
        if current_user.role != "admin":
            raise ForbiddenException("Only admins can manage categories")
        if self.product_repo.get_category_by_name(data.name):
            raise ConflictException(f"Category '{data.name}' already exists")
        if data.parent_id:
            parent = self.product_repo.get_category(data.parent_id)
            if not parent:
                raise NotFoundException("Parent category not found")
        cat = self.product_repo.create_category(data)
        return CategoryResponse.model_validate(cat)

    def update_category(self, cat_id: str, data: CategoryUpdate, current_user: User) -> CategoryResponse:
        if current_user.role != "admin":
            raise ForbiddenException("Only admins can manage categories")
        cat = self.product_repo.get_category(cat_id)
        if not cat:
            raise NotFoundException("Category not found")
        if data.parent_id is not None:
            if data.parent_id == cat_id:
                raise BadRequestException("A category cannot be its own parent")
            parent = self.product_repo.get_category(data.parent_id)
            if not parent:
                raise NotFoundException("Parent category not found")
            # Prevent cycles: the new parent must not live under this category.
            descendants = self.product_repo.get_category_descendant_ids(cat_id)
            if data.parent_id in descendants:
                raise BadRequestException(
                    "Cannot set a descendant category as this category's parent"
                )
        updated = self.product_repo.update_category(cat, data)
        return CategoryResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # Brands
    # ------------------------------------------------------------------

    def get_brands(self) -> List[BrandResponse]:
        brands = self.product_repo.get_brands()
        return [BrandResponse.model_validate(b) for b in brands]

    def create_brand(self, data: BrandCreate, current_user: User) -> BrandResponse:
        if current_user.role != "admin":
            raise ForbiddenException("Only admins can manage brands")
        if self.product_repo.get_brand_by_name(data.name):
            raise ConflictException(f"Brand '{data.name}' already exists")
        brand = self.product_repo.create_brand(data)
        return BrandResponse.model_validate(brand)

    def update_brand(self, brand_id: str, data: BrandUpdate, current_user: User) -> BrandResponse:
        if current_user.role != "admin":
            raise ForbiddenException("Only admins can manage brands")
        brand = self.product_repo.get_brand(brand_id)
        if not brand:
            raise NotFoundException("Brand not found")
        updated = self.product_repo.update_brand(brand, data)
        return BrandResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def list_products(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        brand_id: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        in_stock: Optional[bool] = None,
        has_discount: Optional[bool] = None,
        sort: str = "newest",
        page: int = 1,
        limit: int = 24,
        seller_id: Optional[str] = None,
        include_inactive: bool = False,
        current_user: Optional[User] = None,
    ) -> PaginatedProducts:
        # Server-side scoping for inactive (unpublished) products:
        # - anonymous / customer: never
        # - seller: only their own catalog (any client-supplied seller_id is ignored)
        # - admin: any catalog
        if include_inactive:
            if current_user is None:
                raise UnauthorizedException("Authentication required")
            if current_user.role == "seller":
                seller_id = current_user.id
            elif current_user.role != "admin":
                raise ForbiddenException("Not authorized to list inactive products")

        skip = (page - 1) * limit
        min_d = Decimal(str(min_price)) if min_price is not None else None
        max_d = Decimal(str(max_price)) if max_price is not None else None
        products, total = self.product_repo.list_products(
            q=q, category=category, brand_id=brand_id,
            min_price=min_d, max_price=max_d, min_rating=min_rating,
            in_stock=in_stock, has_discount=has_discount,
            sort=sort, skip=skip, limit=limit,
            seller_id=seller_id, include_inactive=include_inactive,
        )
        return PaginatedProducts(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            page=page,
            limit=limit,
        )

    def get_product(self, product_id: str, current_user: Optional[User] = None) -> ProductResponse:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        # Inactive products are hidden from the public catalog — only the
        # owning seller (or an admin) may still fetch them.
        if not product.is_active:
            if current_user is None or (
                product.seller_id != current_user.id
                and current_user.role != "admin"
            ):
                raise NotFoundException("Product not found")
        return ProductResponse.model_validate(product)

    def create_product(self, data: ProductCreate, current_user: User) -> ProductResponse:
        if current_user.role not in ("seller", "admin"):
            raise ForbiddenException("Only sellers and admins can create products")
        cat = self.product_repo.get_category(data.category_id)
        if not cat:
            raise NotFoundException("Category not found")
        if data.brand_id:
            brand = self.product_repo.get_brand(data.brand_id)
            if not brand:
                raise NotFoundException("Brand not found")
        product = None
        try:
            product = self.product_repo.create_product(data, seller_id=current_user.id)
        except IntegrityError:
            self.product_repo.db.rollback()
            raise ConflictException("A product with this SKU already exists") from None
        # Every product needs its inventory row: without it the seller inventory
        # endpoints 404 and checkout silently skips stock reservation.
        if self.inventory_repo is not None:
            try:
                self.inventory_repo.create_for_product(
                    product.id, initial_stock=data.stock
                )
            except IntegrityError:
                # Concurrent creation of the same row — it already exists.
                self.inventory_repo.db.rollback()
        return ProductResponse.model_validate(product)

    def update_product(self, product_id: str, data: ProductUpdate, current_user: User) -> ProductResponse:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        if product.seller_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized to update this product")

        # When a product has active variants, its stock is derived from them
        # (variant stock linkage). Editing product.stock directly would fight
        # that derivation, so sellers must change stock on the variants.
        if data.stock is not None and any(v.is_active for v in product.variants):
            raise BadRequestException(
                "This product has active variants — set stock on the variants instead"
            )

        # Validate the stock change against reservations BEFORE committing, so
        # product.stock and inventory.physical_stock cannot diverge on failure.
        if data.stock is not None and self.inventory_repo is not None:
            inv = self.inventory_repo.get_by_product(product.id)
            if inv is not None and data.stock < inv.reserved_stock:
                raise BadRequestException(
                    f"Cannot set stock to {data.stock}: {inv.reserved_stock} units are reserved"
                )

        updated = None
        try:
            updated = self.product_repo.update_product(product, data)
        except IntegrityError:
            self.product_repo.db.rollback()
            raise ConflictException("A product with this SKU already exists") from None

        # Mirror catalog stock changes into the inventory ledger.
        if data.stock is not None and self.inventory_repo is not None:
            inv = self.inventory_repo.get_by_product(updated.id)
            if inv is None:
                try:
                    self.inventory_repo.create_for_product(
                        updated.id, initial_stock=updated.stock
                    )
                except IntegrityError:
                    self.inventory_repo.db.rollback()
            elif updated.stock != inv.physical_stock:
                self.inventory_repo.set_stock(
                    inv,
                    physical_stock=updated.stock,
                    actor_id=current_user.id,
                    note="Synced from product update",
                )
        return ProductResponse.model_validate(updated)

    def delete_product(self, product_id: str, current_user: User) -> None:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        if product.seller_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized to delete this product")
        self.product_repo.delete_product(product)

    def search_suggestions(self, q: str) -> List[str]:
        if not q or len(q) < 2:
            return []
        return self.product_repo.search_suggestions(q, limit=8)

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def add_image(self, product_id: str, data: ProductImageCreate, current_user: User) -> ProductImageResponse:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        if product.seller_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized")
        img = self.product_repo.add_image(product_id, data)
        return ProductImageResponse.model_validate(img)

    def upload_image(self, product_id: str, file, current_user: User) -> ProductImageResponse:
        """Upload a local image file for a product (seller/admin only)."""
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        if product.seller_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized")
        url = self.image_storage.save(file)
        img = self.product_repo.add_image(
            product_id, ProductImageCreate(url=url, sort_order=len(product.images))
        )
        return ProductImageResponse.model_validate(img)

    def delete_image(self, image_id: str, current_user: User) -> None:
        img = self.product_repo.get_image(image_id)
        if not img:
            raise NotFoundException("Image not found")
        product = self.product_repo.get_product(img.product_id)
        if product.seller_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized")
        url = img.url
        self.product_repo.delete_image(img)
        self.image_storage.delete(url)

    # ------------------------------------------------------------------
    # Variants
    # ------------------------------------------------------------------

    def create_variant(self, product_id: str, data: ProductVariantCreate, current_user: User) -> ProductVariantResponse:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        if product.seller_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized")
        variant = self.product_repo.create_variant(product_id, data)
        self._recompute_variant_stock(product, current_user)
        return ProductVariantResponse.model_validate(variant)

    def update_variant(self, variant_id: str, data: ProductVariantUpdate, current_user: User) -> ProductVariantResponse:
        variant = self.product_repo.get_variant(variant_id)
        if not variant:
            raise NotFoundException("Variant not found")
        product = self.product_repo.get_product(variant.product_id)
        if product.seller_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized")
        updated = self.product_repo.update_variant(variant, data)
        self._recompute_variant_stock(product, current_user)
        return ProductVariantResponse.model_validate(updated)

    def delete_variant(self, variant_id: str, current_user: User) -> None:
        variant = self.product_repo.get_variant(variant_id)
        if not variant:
            raise NotFoundException("Variant not found")
        product = self.product_repo.get_product(variant.product_id)
        if product.seller_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized")
        self.product_repo.delete_variant(variant)
        self._recompute_variant_stock(product, current_user)

    def _recompute_variant_stock(self, product, current_user: User) -> None:
        """Variant stock linkage: product.stock mirrors the sum of ACTIVE
        variant stocks, and the inventory physical stock follows."""
        if self.inventory_repo is None:
            return
        fresh = self.product_repo.get_product(product.id)
        total = sum(v.stock for v in fresh.variants if v.is_active)
        if fresh.stock == total:
            return
        # Reserved units must not be lost when shrinking stock.
        inv = self.inventory_repo.get_by_product(fresh.id)
        reserved = inv.reserved_stock if inv else 0
        if total < reserved:
            raise BadRequestException(
                f"Cannot reduce stock to {total}: {reserved} units are reserved"
            )
        fresh.stock = total
        self.product_repo.db.commit()
        inv = self.inventory_repo.get_by_product(fresh.id)
        if inv is not None:
            self.inventory_repo.set_stock(
                inv,
                physical_stock=total,
                actor_id=current_user.id,
                note="Synced from variant stock",
            )
        else:
            try:
                self.inventory_repo.create_for_product(fresh.id, initial_stock=total)
            except IntegrityError:
                self.inventory_repo.db.rollback()

    # ------------------------------------------------------------------
    # Related products
    # ------------------------------------------------------------------

    def get_related_products(self, product_id: str, limit: int = 8) -> List[ProductResponse]:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        related = self.product_repo.get_related_products(product, limit=limit)
        return [ProductResponse.model_validate(p) for p in related]

    # ------------------------------------------------------------------
    # Reviews (eligibility is derived from backend order data; moderation is
    # admin-controlled; `is_verified` is never client-supplied)
    # ------------------------------------------------------------------

    def get_reviews(self, product_id: str, current_user: Optional[User] = None) -> List[ReviewResponse]:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        viewer_id = current_user.id if current_user else None
        reviews = self.product_repo.get_reviews(product_id, viewer_id=viewer_id)
        return [ReviewResponse.model_validate(r) for r in reviews]

    def add_review(self, product_id: str, data: ReviewCreate, current_user: User) -> ReviewResponse:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")

        # One review per user per product.
        existing = self.product_repo.get_review_by_user_product(current_user.id, product_id)
        if existing:
            raise ConflictException("You have already reviewed this product")

        # Eligibility + verified badge come from backend order data, never from
        # the client.
        if self.order_repo is None:
            raise BadRequestException("Review eligibility is unavailable")
        purchased = self.order_repo.has_paid_purchase(current_user.id, product_id)
        if not purchased:
            raise BadRequestException(
                "Only verified purchasers can review this product"
            )
        delivered = self.order_repo.has_paid_purchase(
            current_user.id, product_id, delivered=True
        )

        review = self.product_repo.create_review(
            data=data,
            product_id=product_id,
            user_id=current_user.id,
            user_name=current_user.full_name,
            is_verified=delivered,
        )
        # Pending reviews are not yet part of the published rating.
        self.product_repo.db.commit()
        return ReviewResponse.model_validate(review)

    # --- moderation (admin) ---

    def list_reviews_for_moderation(
        self, current_user: User, moderation_status: Optional[str] = None
    ) -> List[ReviewResponse]:
        if current_user.role != "admin":
            raise ForbiddenException("Only admins can moderate reviews")
        reviews = self.product_repo.get_all_reviews(moderation_status)
        return [ReviewResponse.model_validate(r) for r in reviews]

    def moderate_review(
        self, review_id: str, action: str, current_user: User
    ) -> ReviewResponse:
        if current_user.role != "admin":
            raise ForbiddenException("Only admins can moderate reviews")
        review = self.product_repo.get_review(review_id)
        if not review:
            raise NotFoundException("Review not found")
        if action == "approve":
            self.product_repo.set_review_moderation(review, "approved")
        else:
            self.product_repo.set_review_moderation(review, "rejected")
        product = self.product_repo.get_product(review.product_id)
        if product:
            # Recompute the published aggregate (approved only).
            self.product_repo.update_product_rating(product)
        else:
            self.product_repo.db.commit()
        return ReviewResponse.model_validate(review)
