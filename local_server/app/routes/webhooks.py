"""
Payment Webhook Handlers
Handles callbacks from Paystack and KongaPay
"""

from fastapi import APIRouter, Request, HTTPException
from prisma import Prisma
from shared.database import get_db
from fastapi import Depends
import hashlib
import hmac
import json
from typing import Dict, Any

router = APIRouter()


class PaystackWebhook:
    """Paystack webhook handler."""
    
    @staticmethod
    def verify_signature(payload: bytes, signature: str, secret_key: str) -> bool:
        """Verify Paystack webhook signature."""
        hash_obj = hmac.new(
            secret_key.encode("utf-8"),
            payload,
            hashlib.sha512,
        )
        computed_signature = hash_obj.hexdigest()
        return hmac.compare_digest(computed_signature, signature)
    
    @staticmethod
    async def handle(event_data: Dict[str, Any], db: Prisma) -> Dict[str, Any]:
        """Handle Paystack webhook event."""
        event = event_data.get("event")
        data = event_data.get("data", {})
        
        if event == "charge.success":
            return await PaystackWebhook._handle_successful_charge(data, db)
        elif event == "charge.failed":
            return await PaystackWebhook._handle_failed_charge(data, db)
        elif event == "transfer.success":
            return await PaystackWebhook._handle_successful_transfer(data, db)
        else:
            return {"status": "ignored", "event": event}
    
    @staticmethod
    async def _handle_successful_charge(data: Dict[str, Any], db: Prisma) -> Dict[str, Any]:
        """Handle successful charge."""
        reference = data.get("reference")
        amount = data.get("amount", 0) / 100  # Convert from kobo
        
        # Find and update payment
        payment = await db.payment.find_unique(where={"reference": reference})
        if payment:
            await db.payment.update(
                where={"id": payment.id},
                data={
                    "status": "completed",
                    "paymentReference": data.get("id"),
                },
            )
            
            # Update session if linked
            if payment.sessionId:
                await db.session.update(
                    where={"id": payment.sessionId},
                    data={"amountCharged": payment.amount},
                )
            
            return {"status": "success", "payment_id": payment.id}
        
        return {"status": "not_found", "reference": reference}
    
    @staticmethod
    async def _handle_failed_charge(data: Dict[str, Any], db: Prisma) -> Dict[str, Any]:
        """Handle failed charge."""
        reference = data.get("reference")
        
        payment = await db.payment.find_unique(where={"reference": reference})
        if payment:
            await db.payment.update(
                where={"id": payment.id},
                data={"status": "failed"},
            )
            return {"status": "updated", "payment_id": payment.id}
        
        return {"status": "not_found", "reference": reference}
    
    @staticmethod
    async def _handle_successful_transfer(data: Dict[str, Any], db: Prisma) -> Dict[str, Any]:
        """Handle successful transfer (payout)."""
        # Log transfer for audit
        return {"status": "logged", "transfer": data.get("reference")}


class KongaPayWebhook:
    """KongaPay webhook handler."""
    
    @staticmethod
    async def handle(event_data: Dict[str, Any], db: Prisma) -> Dict[str, Any]:
        """Handle KongaPay webhook event."""
        status = event_data.get("status")
        transaction_id = event_data.get("transactionId")
        
        if status == "successful":
            return await KongaPayWebhook._handle_successful_payment(event_data, db)
        elif status == "failed":
            return await KongaPayWebhook._handle_failed_payment(event_data, db)
        
        return {"status": "ignored", "status": status}
    
    @staticmethod
    async def _handle_successful_payment(data: Dict[str, Any], db: Prisma) -> Dict[str, Any]:
        """Handle successful KongaPay payment."""
        order_id = data.get("orderId")
        
        # Find payment by local_id (order_id)
        payment = await db.payment.find_unique(where={"localId": order_id})
        if payment:
            await db.payment.update(
                where={"id": payment.id},
                data={
                    "status": "completed",
                    "paymentReference": data.get("transactionId"),
                },
            )
            return {"status": "success", "payment_id": payment.id}
        
        return {"status": "not_found", "order_id": order_id}
    
    @staticmethod
    async def _handle_failed_payment(data: Dict[str, Any], db: Prisma) -> Dict[str, Any]:
        """Handle failed KongaPay payment."""
        order_id = data.get("orderId")
        
        payment = await db.payment.find_unique(where={"localId": order_id})
        if payment:
            await db.payment.update(
                where={"id": payment.id},
                data={"status": "failed"},
            )
            return {"status": "updated", "payment_id": payment.id}
        
        return {"status": "not_found", "order_id": order_id}


@router.post("/paystack")
async def paystack_webhook(request: Request, db: Prisma = Depends(get_db)):
    """Handle Paystack webhook."""
    from shared.config import settings
    
    # Get signature
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Get body
    body = await request.body()
    
    # Verify signature
    if not PaystackWebhook.verify_signature(body, signature, settings.PAYSTACK_SECRET_KEY):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Parse and handle event
    try:
        event_data = json.loads(body)
        result = await PaystackWebhook.handle(event_data, db)
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")


@router.post("/kongapay")
async def kongapay_webhook(request: Request, db: Prisma = Depends(get_db)):
    """Handle KongaPay webhook."""
    body = await request.body()
    
    try:
        event_data = json.loads(body)
        result = await KongaPayWebhook.handle(event_data, db)
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")


@router.get("/status/{reference}")
async def get_payment_webhook_status(reference: str, db: Prisma = Depends(get_db)):
    """Check payment status via webhook."""
    payment = await db.payment.find_unique(where={"reference": reference})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "reference": payment.reference,
        "status": payment.status,
        "amount": payment.amount,
        "method": payment.method,
        "created_at": payment.createdAt,
        "updated_at": payment.updatedAt,
    }
