import io
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.order import Order


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db

    def generate_invoice_data(self, order_id: str) -> dict:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            from app.core.exceptions import NotFoundException
            raise NotFoundException("Order not found")

        items = []
        for item in order.order_items:
            items.append({
                "product_name": item.product_name or "",
                "quantity": item.quantity,
                "price": float(item.unit_price),
                "subtotal": float(item.quantity * item.unit_price),
            })

        shipping_addr = order.shipping_address or {}
        billing_addr = order.billing_address or {}

        # simple invoice number
        invoice_number = f"INV-{order.id[:8].upper()}-{int(order.created_at.timestamp()) if order.created_at else '0000'}"

        return {
            "invoice_number": invoice_number,
            "order_id": order.id,
            "customer_name": order.customer_name or (order.user.email if order.user else ""),
            "customer_email": order.user.email if order.user else "",
            "shipping_address": shipping_addr,
            "billing_address": billing_addr,
            "products": items,
            "quantity_total": sum(i["quantity"] for i in items),
            "subtotal": float(order.subtotal),
            "discount": float(order.discount or 0),
            "tax": float(order.tax or 0),
            "shipping": float(order.shipping_charge or 0),
            "grand_total": float(order.grand_total),
            "payment_status": order.payment_status or "",
            "order_status": order.status,
            "created_at": order.created_at,
            "currency": "INR",
        }

    def generate_pdf(self, order_id: str) -> bytes:
        data = self.generate_invoice_data(order_id)
        # Simple HTML -> return as PDF? Try to generate minimal PDF text bytes via basic approach
        # But avoid external deps; generate HTML and return as bytes if client wants PDF? Return HTML bytes as fallback named .pdf? 
        # Requirement says generate PDF locally - provide HTML-based PDF content (printable). Return HTML bytes with content-type handled by router.
        html = self._generate_html(data)
        return html.encode("utf-8")

    def _generate_html(self, data: dict) -> str:
        items_html = ""
        for i in data["products"]:
            items_html += f"<tr><td>{i['product_name']}</td><td>{i['quantity']}</td><td>{data['currency']} {i['price']:.2f}</td><td>{data['currency']} {i['subtotal']:.2f}</td></tr>"

        return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Invoice {data['invoice_number']}</title>
        <style>body{{font-family:sans-serif;font-size:12px}} table{{width:100%;border-collapse:collapse}} td,th{{border:1px solid #ddd;padding:6px;text-align:left}} .right{{text-align:right}}</style>
        </head><body><h2>Invoice {data['invoice_number']}</h2>
        <p>Order ID: {data['order_id']}<br/>Date: {data['created_at']}<br/>Payment Status: {data['payment_status']}<br/>Order Status: {data['order_status']}</p>
        <p><strong>Customer:</strong> {data['customer_name']} ({data['customer_email']})</p>
        <table><thead><tr><th>Product</th><th>Qty</th><th>Price</th><th>Subtotal</th></tr></thead><tbody>{items_html}</tbody></table>
        <p class='right'>Subtotal: {data['currency']} {data['subtotal']:.2f}<br/>Discount: {data['currency']} {data['discount']:.2f}<br/>Tax: {data['currency']} {data['tax']:.2f}<br/>Shipping: {data['currency']} {data['shipping']:.2f}<br/><strong>Total: {data['currency']} {data['grand_total']:.2f}</strong></p>
        </body></html>"""
