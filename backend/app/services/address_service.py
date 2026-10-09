"""Address-book service — CRUD + default handling for the current user."""
from __future__ import annotations

from typing import List

from app.core.exceptions import NotFoundException
from app.models.user import User
from app.repositories.address_repo import AddressRepository
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate


class AddressService:
    def __init__(self, address_repo: AddressRepository):
        self.address_repo = address_repo

    def list_addresses(self, current_user: User) -> List[AddressResponse]:
        return [
            AddressResponse.model_validate(a)
            for a in self.address_repo.list_user_addresses(current_user.id)
        ]

    def create_address(self, data: AddressCreate, current_user: User) -> AddressResponse:
        address = self.address_repo.create(current_user.id, data)
        return AddressResponse.model_validate(address)

    def update_address(
        self, address_id: str, data: AddressUpdate, current_user: User
    ) -> AddressResponse:
        address = self.address_repo.get_user_address(current_user.id, address_id)
        if not address:
            raise NotFoundException("Address not found")
        return AddressResponse.model_validate(
            self.address_repo.update(address, data)
        )

    def set_default(self, address_id: str, current_user: User) -> AddressResponse:
        address = self.address_repo.get_user_address(current_user.id, address_id)
        if not address:
            raise NotFoundException("Address not found")
        return AddressResponse.model_validate(
            self.address_repo.set_default(current_user.id, address)
        )

    def delete_address(self, address_id: str, current_user: User) -> None:
        """Soft delete: historical order snapshots are unaffected."""
        address = self.address_repo.get_user_address(current_user.id, address_id)
        if not address:
            raise NotFoundException("Address not found")
        self.address_repo.deactivate(address)