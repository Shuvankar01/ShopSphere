"""Return (RMA) service — controlled states, separate from payment state.

Customer: request / view / cancel. Admin: approve / reject / receive / complete
and initiate a DEMO refund for the returned items. Refund state lives on the
Refund/Payment domain — it never mixes with the return state.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.core.logging import logger
from app.models.user import User
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.return_repo import ReturnRepository
from app.schemas.refund import RefundCreate
from app.schemas.return_request import (
    RETURN_TRANSITIONS,
    ReturnCreate,
    ReturnResponse,
)
from app.services.refund_service import RefundService


class ReturnService:
    def __init__(
        self,
        return_repo: ReturnRepository,
        order_repo: OrderRepository,
        payment_repo: PaymentRepository,
        refund_service: Optional[RefundService] = None,
    ):
        self.return_repo = return_repo
        self.order_repo = order_repo
        self.payment_repo = payment_repo
        self.refund_service = refund_service

    def _get_owned(self, return_id: str, current_user: User) -> "Return":
        ret = self.return_repo.get(return_id)
        if not ret:
            raise NotFoundException("Return request not found")
        if ret.user_id != current_user.id and current_user.role != "admin":
            raise NotFoundException("Return request not found")
        return ret

    def _require_admin(self, user: User) -> None:
        if user.role != "admin":
            raise ForbiddenException("Only admins can moderate returns")

    def _transition(self, ret: "Return", new_status: str, actor: str, reason: Optional[str] = None) -> None:
        allowed = RETURN_TRANSITIONS.get(ret.status, set())
        if new_status not in allowed:
            raise BadRequestException(
                f"Cannot move return from '{ret.status}' to '{new_status}'. "
                f"Allowed: {sorted(allowed) or 'none'}"
            )
        self.return_repo.set_status(ret, new_status)
        logger.info(f"Return {ret.id}: {ret.status} -> {new_status} by {actor} ({reason or 'no reason'})")

    # ------------------------------------------------------------------
    # Customer
    # ------------------------------------------------------------------

    def create_return(self, data: ReturnCreate, current_user: User) -> ReturnResponse:
        order = self.order_repo.get_order(data.order_id)
        if not order or order.user_id != current_user.id:
            raise NotFoundException("Order not found")
        if order.order_status != "delivered":
            raise BadRequestException("Returns are only accepted for delivered orders")

        order_items = {item.id: item for item in order.items}
        ret = self.return_repo.create(current_user.id, order.id, data.reason)
        for line in data.items:
            item = order_items.get(line.order_item_id)
            if item is None:
                raise BadRequestException(
                    f"Order item '{line.order_item_id}' is not part of this order"
                )
            already = self.return_repo.returned_quantity(item.id)
            remaining = item.quantity - already
            if line.quantity > remaining:
                raise BadRequestException(
                    f"Only {remaining} unit(s) of '{item.product_name}' can be returned"
                )
            self.return_repo.add_item(ret.id, item.id, line.quantity, line.reason)

        self.return_repo.set_status(ret, "requested")
        self.payment_repo.db.commit()
        return ReturnResponse.model_validate(ret)

    def list_returns(self, current_user: User) -> List[ReturnResponse]:
        return [
            ReturnResponse.model_validate(r)
            for r in self.return_repo.get_user_returns(current_user.id)
        ]

    def get_return(self, return_id: str, current_user: User) -> ReturnResponse:
        ret = self._get_owned(return_id, current_user)
        return ReturnResponse.model_validate(ret)

    def cancel_return(self, return_id: str, current_user: User) -> ReturnResponse:
        ret = self._get_owned(return_id, current_user)
        if ret.user_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized to cancel this return")
        self._transition(ret, "cancelled", current_user.id, "Customer cancelled")
        self.payment_repo.db.commit()
        return ReturnResponse.model_validate(ret)

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    def list_all(self, current_user: User, order_id: Optional[str] = None) -> List[ReturnResponse]:
        self._require_admin(current_user)
        returns = (
            self.return_repo.get_returns_for_order(order_id)
            if order_id
            else self.return_repo.get_all()
        )
        return [ReturnResponse.model_validate(r) for r in returns]

    def approve(self, return_id: str, current_user: User, reason: Optional[str] = None) -> ReturnResponse:
        self._require_admin(current_user)
        ret = self.return_repo.get(return_id)
        if not ret:
            raise NotFoundException("Return request not found")
        self._transition(ret, "approved", current_user.id, reason)
        self.payment_repo.db.commit()
        return ReturnResponse.model_validate(ret)

    def reject(self, return_id: str, current_user: User, reason: Optional[str] = None) -> ReturnResponse:
        self._require_admin(current_user)
        ret = self.return_repo.get(return_id)
        if not ret:
            raise NotFoundException("Return request not found")
        self._transition(ret, "rejected", current_user.id, reason or "Rejected by admin")
        self.payment_repo.db.commit()
        return ReturnResponse.model_validate(ret)

    def mark_received(self, return_id: str, current_user: User, reason: Optional[str] = None) -> ReturnResponse:
        self._require_admin(current_user)
        ret = self.return_repo.get(return_id)
        if not ret:
            raise NotFoundException("Return request not found")
        self._transition(ret, "received", current_user.id, reason or "Item received")
        self.payment_repo.db.commit()
        return ReturnResponse.model_validate(ret)

    def complete(self, return_id: str, current_user: User, reason: Optional[str] = None) -> ReturnResponse:
        self._require_admin(current_user)
        ret = self.return_repo.get(return_id)
        if not ret:
            raise NotFoundException("Return request not found")
        self._transition(ret, "completed", current_user.id, reason or "Return processed")
        self.payment_repo.db.commit()
        return ReturnResponse.model_validate(ret)

    def refund_amount(self, ret: "Return") -> Decimal:
        """Total value of the returned lines, from the immutable order snapshot."""
        items_by_id = {i.id: i for i in ret.order.items}
        total = Decimal("0.00")
        for line in ret.items:
            item = items_by_id.get(line.order_item_id)
            if item:
                total += Decimal(str(item.price)) * line.quantity
        return total

    def initiate_refund(self, return_id: str, current_user: User) -> dict:
        """Admin: initiate a DEMO refund for a completed return. Idempotent via a
        per-return idempotency key (no double refund)."""
        self._require_admin(current_user)
        ret = self.return_repo.get(return_id)
        if not ret:
            raise NotFoundException("Return request not found")
        if ret.status != "completed":
            raise BadRequestException("Refunds are only issued for completed returns")

        amount = self.refund_amount(ret)
        if amount <= 0:
            raise BadRequestException("Return has no refundable amount")

        refund = self.refund_service.create_refund(
            RefundCreate(
                order_id=ret.order_id,
                amount=amount,
                reason=f"Refund for return {ret.id}",
                idempotency_key=f"return:{ret.id}",
            ),
            current_user,
        )
        return {"refund": refund.model_dump(mode="json"), "return_status": ret.status}