import hashlib
import hmac
import base64
import os
from decimal import Decimal

from django.conf import settings

def generate_phonepe_checksum(payload_base64, api_endpoint):
    salt_key = settings.PHONEPE_CONFIG['CLIENT_SECRET']
    string_to_sign = f"{payload_base64}{api_endpoint}{salt_key}"
    checksum = hmac.new(
        salt_key.encode(),
        string_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{checksum}###1"


# def calculate_order_amount(order):
#     subtotal = sum(item.product_variant.price * item.quantity for item in order.items.all())
#     tax_percent = Decimal(os.getenv('TAX_PERCENT', '5'))
#     handling_charge = Decimal(os.getenv('HANDLING_CHARGE', '10'))
#     delivery_charge = Decimal(os.getenv('DELIVERY_CHARGE', '30'))
#
#     tax = subtotal * (tax_percent / Decimal('100'))
#     return subtotal + tax + handling_charge + delivery_charge
