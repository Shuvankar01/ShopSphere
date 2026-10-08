"""Payment service — demo payment processing (no external provider).

The server validates ownership and order state, records the Payment and
PaymentTransaction rows, and transitions the order — it never trusts a
client-supplied success flag.
"""
from __future__ import annotations

from app.core.exceptions import ConflictException, NotFoundException
from app.core.logging import logger
from app.models.user import User
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import PaymentCreate, PaymentResponse


class PaymentService:
    def __init__(
        self,
        order_repo: OrderRepository,
        payment_repo: PaymentRepository,
    ):
        self.order_repo = order_repo
        self.payment_repo = payment_repo

    def create_payment(self, data: PaymentCreate, current_user: User) -> PaymentResponse:
        order = self.order_repo.get_order(data.order_id)
        # IDOR: a foreign order is indistinguishable from a missing one.
        if not order or order.user_id != current_user.id:
            raise NotFoundException("Order not found")

        if order.payment_status == "paid":
            raise ConflictException("Order is already paid")
        if order.payment_status == "refunded":
            raise ConflictException("Order has been refunded")
        if order.order_status == "cancelled":
            raise ConflictException("Order is cancelled and cannot be paid")

        payment, transaction = self.payment_repo.create_charge(
            order=order,
            user_id=current_user.id,
            payment_method=data.payment_method,
            amount=order.total_amount,
        )

        # Server-side order transitions (demo: payments settle immediately).
        order.payment_status = "paid"
        if order.order_status == "pending":
            order.order_status = "confirmed"
            self.order_repo.add_status_history(
                order_id=order.id,
                from_status="pending",
                to_status="confirmed",
                changed_by=current_user.id,
                note=f"Payment {transaction.reference}",
            )
        self.payment_repo.db.commit()

        logger.info(
            f"Payment {transaction.reference} for order {order.id} "
            f"by user {current_user.id} amount={order.total_amount}"
        )
        return PaymentResponse(
            transaction_id=transaction.reference,
            status="succeeded",
        )
