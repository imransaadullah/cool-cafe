from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from shared.database import get_db
from ..services.payment import payment_service
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

router = APIRouter()


class PaymentInitRequest(BaseModel):
    method: str
    amount: float
    email: Optional[str] = None
    session_id: Optional[int] = None
    branch_id: int


class PaymentResponse(BaseModel):
    success: bool
    message: str
    payment_url: Optional[str] = None
    reference: Optional[str] = None


class PaymentVerifyRequest(BaseModel):
    method: str
    reference: str


@router.post("/initialize", response_model=PaymentResponse)
async def initialize_payment(
    request: PaymentInitRequest,
    db: Prisma = Depends(get_db),
):
    """Initialize a payment."""
    reference = f"CC_{uuid.uuid4().hex[:12].upper()}"
    
    # Create payment record
    payment = await db.payment.create(
        data={
            "sessionId": request.session_id,
            "branchId": request.branch_id,
            "amount": request.amount,
            "method": request.method,
            "reference": reference,
            "status": "pending",
            "localId": str(uuid.uuid4()),
        }
    )
    
    if request.method in ["paystack", "konga_pay"]:
        # Process online payment
        result = await payment_service.process_payment(
            method=request.method,
            amount=request.amount,
            email=request.email,
            reference=reference,
        )
        
        if result.get("status"):
            return PaymentResponse(
                success=True,
                message="Payment initialized",
                payment_url=result.get("data", {}).get("authorization_url"),
                reference=reference,
            )
        else:
            return PaymentResponse(
                success=False,
                message=result.get("message", "Payment initialization failed"),
            )
    
    elif request.method == "cash":
        # Cash payment - mark as completed immediately
        await db.payment.update(
            where={"id": payment.id},
            data={"status": "completed"},
        )
        
        return PaymentResponse(
            success=True,
            message="Cash payment recorded",
            reference=reference,
        )
    
    elif request.method == "code":
        return PaymentResponse(
            success=False,
            message="Use code redemption endpoint",
        )
    
    else:
        return PaymentResponse(
            success=False,
            message=f"Unsupported payment method: {request.method}",
        )


@router.post("/verify", response_model=PaymentResponse)
async def verify_payment(
    request: PaymentVerifyRequest,
    db: Prisma = Depends(get_db),
):
    """Verify a payment."""
    payment = await db.payment.find_unique(where={"reference": request.reference})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if request.method in ["paystack", "konga_pay"]:
        result = await payment_service.verify_payment(
            method=request.method,
            reference=request.reference,
        )
        
        if result.get("status") and result.get("data", {}).get("status") == "success":
            await db.payment.update(
                where={"id": payment.id},
                data={"status": "completed"},
            )
            
            return PaymentResponse(
                success=True,
                message="Payment verified successfully",
                reference=request.reference,
            )
        else:
            return PaymentResponse(
                success=False,
                message="Payment verification failed",
            )
    
    return PaymentResponse(
        success=False,
        message="Unsupported payment method",
    )


@router.get("/{reference}")
async def get_payment_status(reference: str, db: Prisma = Depends(get_db)):
    """Get payment status."""
    payment = await db.payment.find_unique(where={"reference": reference})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "reference": payment.reference,
        "status": payment.status,
        "amount": payment.amount,
        "method": payment.method,
        "created_at": payment.createdAt,
    }
