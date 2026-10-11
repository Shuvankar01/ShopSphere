from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.dependencies.roles import require_admin
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.models.inventory import Inventory

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", dependencies=[Depends(require_admin)])
def dashboard(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0

    revenue_q = db.query(
        func.coalesce(func.sum(Order.grand_total), 0)
    ).filter(Order.status.in_(["paid", "confirmed", "processing", "packed", "shipped", "out_for_delivery", "delivered"]))
    revenue = float(revenue_q.scalar() or 0)

    low_stock = db.query(func.count(Inventory.id)).filter(Inventory.stock_quantity <= Inventory.low_stock_threshold).scalar() or 0

    if total_orders > 0:
        avg_order_value = revenue / total_orders
    else:
        avg_order_value = 0.0

    # last 7 days sales
    start = now - timedelta(days=7)
    daily = db.query(
        func.date_trunc('day', Order.created_at).label("day"),
        func.coalesce(func.sum(Order.grand_total), 0).label("total"),
        func.count(Order.id).label("count"),
    ).filter(Order.created_at >= start).group_by("day").order_by("day").all()

    sales_analytics = [
        {"date": d.day.isoformat() if hasattr(d.day, "isoformat") else str(d.day), "revenue": float(d.total), "orders": int(d.count)}
        for d in daily
    ]

    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "revenue": revenue,
        "low_stock_products": low_stock,
        "average_order_value": round(avg_order_value, 2),
        "sales_analytics": sales_analytics,
    }
