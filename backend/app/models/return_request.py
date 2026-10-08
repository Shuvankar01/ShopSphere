"""Returns domain: return requests and their line items (foundation for RMA flow)."""
import uuid
from sqlalchemy import (
    Column, String, Integer, ForeignKey, DateTime, Text, CheckConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Return(Base):
    __tablename__ = "returns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="requested")
    # requested / approved / rejected / completed
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items = relationship("ReturnItem", back_populates="return_request", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('requested', 'approved', 'rejected', 'completed')",
            name="ck_return_status",
        ),
    )


class ReturnItem(Base):
    __tablename__ = "return_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    return_id = Column(String, ForeignKey("returns.id"), nullable=False, index=True)
    order_item_id = Column(String, ForeignKey("order_items.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    return_request = relationship("Return", back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_return_item_qty_positive"),
    )
