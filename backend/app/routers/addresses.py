"""Customer address-book router."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.repositories.address_repo import AddressRepository
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate
from app.services.address_service import AddressService

router = APIRouter(prefix="/addresses", tags=["addresses"])


def get_address_service(db: Session = Depends(get_db)) -> AddressService:
    return AddressService(AddressRepository(db))


@router.get("", response_model=List[AddressResponse])
def list_addresses(
    current_user: User = Depends(get_current_active_user),
    svc: AddressService = Depends(get_address_service),
):
    return svc.list_addresses(current_user)


@router.post("", response_model=AddressResponse, status_code=201)
def create_address(
    data: AddressCreate,
    current_user: User = Depends(get_current_active_user),
    svc: AddressService = Depends(get_address_service),
):
    return svc.create_address(data, current_user)


@router.put("/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: str,
    data: AddressUpdate,
    current_user: User = Depends(get_current_active_user),
    svc: AddressService = Depends(get_address_service),
):
    return svc.update_address(address_id, data, current_user)


@router.put("/{address_id}/default", response_model=AddressResponse)
def set_default_address(
    address_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: AddressService = Depends(get_address_service),
):
    return svc.set_default(address_id, current_user)


@router.delete("/{address_id}", status_code=204)
def delete_address(
    address_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: AddressService = Depends(get_address_service),
):
    svc.delete_address(address_id, current_user)