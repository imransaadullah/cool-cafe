import httpx
from typing import Optional, Dict, Any
from shared.config import settings


class PaystackService:
    """Paystack payment integration service."""
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
    
    async def initialize_transaction(
        self,
        email: str,
        amount: float,
        reference: Optional[str] = None,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Initialize a Paystack transaction."""
        async with httpx.AsyncClient() as client:
            data = {
                "email": email,
                "amount": int(amount * 100),  # Convert to kobo
            }
            if reference:
                data["reference"] = reference
            if callback_url:
                data["callback_url"] = callback_url
            if metadata:
                data["metadata"] = metadata
            
            response = await client.post(
                f"{self.BASE_URL}/transaction/initialize",
                json=data,
                headers=self.headers,
            )
            return response.json()
    
    async def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """Verify a Paystack transaction."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/transaction/verify/{reference}",
                headers=self.headers,
            )
            return response.json()
    
    async def create_customer(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Paystack customer."""
        async with httpx.AsyncClient() as client:
            data = {"email": email}
            if first_name:
                data["first_name"] = first_name
            if last_name:
                data["last_name"] = last_name
            if phone:
                data["phone"] = phone
            
            response = await client.post(
                f"{self.BASE_URL}/customer",
                json=data,
                headers=self.headers,
            )
            return response.json()
    
    async def create_plan(
        self,
        name: str,
        amount: float,
        interval: str = "monthly",
    ) -> Dict[str, Any]:
        """Create a Paystack plan."""
        async with httpx.AsyncClient() as client:
            data = {
                "name": name,
                "amount": int(amount * 100),
                "interval": interval,
            }
            
            response = await client.post(
                f"{self.BASE_URL}/plan",
                json=data,
                headers=self.headers,
            )
            return response.json()


class KongaPayService:
    """Konga Pay payment integration service."""
    
    BASE_URL = "https://pay.konga.com/api"
    
    def __init__(self):
        self.merchant_id = settings.KONGA_PAY_MERCHANT_ID
    
    async def initialize_payment(
        self,
        amount: float,
        order_id: str,
        callback_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initialize a Konga Pay payment."""
        async with httpx.AsyncClient() as client:
            data = {
                "merchantId": self.merchant_id,
                "amount": amount,
                "orderId": order_id,
            }
            if callback_url:
                data["callbackUrl"] = callback_url
            
            response = await client.post(
                f"{self.BASE_URL}/payment/initialize",
                json=data,
            )
            return response.json()
    
    async def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Verify a Konga Pay payment."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/payment/verify/{transaction_id}",
                params={"merchantId": self.merchant_id},
            )
            return response.json()


class PaymentService:
    """Unified payment service."""
    
    def __init__(self):
        self.paystack = PaystackService()
        self.konga = KongaPayService()
    
    async def process_payment(
        self,
        method: str,
        amount: float,
        email: Optional[str] = None,
        reference: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Process a payment using the specified method."""
        if method == "paystack":
            return await self.paystack.initialize_transaction(
                email=email,
                amount=amount,
                reference=reference,
                **kwargs,
            )
        elif method == "konga_pay":
            return await self.konga.initialize_payment(
                amount=amount,
                order_id=reference or "",
                **kwargs,
            )
        else:
            return {"status": False, "message": f"Unsupported payment method: {method}"}
    
    async def verify_payment(
        self,
        method: str,
        reference: str,
    ) -> Dict[str, Any]:
        """Verify a payment using the specified method."""
        if method == "paystack":
            return await self.paystack.verify_transaction(reference)
        elif method == "konga_pay":
            return await self.konga.verify_payment(reference)
        else:
            return {"status": False, "message": f"Unsupported payment method: {method}"}


payment_service = PaymentService()
