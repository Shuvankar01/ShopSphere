from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/orders", tags=["invoices"])


def get_invoice_service(db: Session = Depends(get_db)) -> InvoiceService:
    return InvoiceService(db)


@router.get("/{order_id}/invoice.html")
def invoice_html(order_id: str, current_user: User = Depends(get_current_active_user),
                 svc: InvoiceService = Depends(get_invoice_service)):
    data = svc.generate_invoice_data(order_id)
    html = svc._generate_html(data)
    return Response(content=html, media_type="text/html")


@router.get("/{order_id}/invoice.pdf")
def invoice_pdf(order_id: str, current_user: User = Depends(get_current_active_user),
                svc: InvoiceService = Depends(get_invoice_service)):
    # Generate PDF bytes (HTML bytes as fallback) - local generation
    pdf_bytes = svc.generate_pdf(order_id)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=invoice_{order_id}.pdf"
    })
