import hmac, hashlib

RAZORPAY_ORDER_ID = "order_RoD2DaBrGMiYM1"   # from your create API
SIMULATED_PAYMENT_ID = "pay_TESTSIMULATED12345"
RAZORPAY_SECRET = "QWayXrI4StKOIpzt866rMpKU"  # from settings.py

data = f"{RAZORPAY_ORDER_ID}|{SIMULATED_PAYMENT_ID}"
signature = hmac.new(RAZORPAY_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()

print("PAYMENT_ID:", SIMULATED_PAYMENT_ID)
print("ORDER_ID:", RAZORPAY_ORDER_ID)
print("SIGNATURE:", signature)
