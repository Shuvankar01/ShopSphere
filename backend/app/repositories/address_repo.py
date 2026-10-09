"""Customer address-book repository."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.address import Address
from app.schemas.address import AddressCreate, AddressUpdate


class AddressRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_user_addresses(self, user_id: str) -> List[Address]:
        return (
            self.db.query(Address)
            .filter(Address.user_id == user_id, Address.is_active == True)
            .order_by(Address.is_default.desc(), Address.created_at.desc())
            .all()
        )

    def get_user_address(self, user_id: str, address_id: str) -> Optional[Address]:
        return (
            self.db.query(Address)
            .filter(Address.id == address_id, Address.user_id == user_id)
            .first()
        )

    def get_default(self, user_id: str) -> Optional[Address]:
        return (
            self.db.query(Address)
            .filter(
                Address.user_id == user_id,
                Address.is_default == True,
                Address.is_active == True,
            )
            .first()
        )

    def create(self, user_id: str, data: AddressCreate) -> Address:
        address = Address(user_id=user_id, **data.model_dump())
        self.db.add(address)
        self.db.flush()
        # Enforce a single default address per user.
        if address.is_default:
            self._clear_other_defaults(user_id, address.id)
        self.db.commit()
        self.db.refresh(address)
        return address

    def update(self, address: Address, data: AddressUpdate) -> Address:
        changed = False
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(address, field, value)
            changed = True
        if changed:
            if address.is_default:
                self._clear_other_defaults(address.user_id, address.id)
            self.db.commit()
            self.db.refresh(address)
        return address

    def set_default(self, user_id: str, address: Address) -> Address:
        self._clear_other_defaults(user_id, address.id)
        address.is_default = True
        self.db.commit()
        self.db.refresh(address)
        return address

    def deactivate(self, address: Address) -> None:
        address.is_active = False
        address.is_default = False
        self.db.commit()

    def _clear_other_defaults(self, user_id: str, keep_id: str) -> None:
        self.db.query(Address).filter(
            Address.user_id == user_id,
            Address.id != keep_id,
            Address.is_default == True,
        ).update({"is_default": False}, synchronize_session=False)