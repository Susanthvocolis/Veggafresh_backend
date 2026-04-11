import os
import sys
import django
from decimal import Decimal

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svv_store.settings')
django.setup()

from orders.models import Order, OrderItem
from payments.models import Payment

def fix_historical_orders():
    # We fetch orders where final_amount is effectively 0.00
    orders = Order.objects.filter(total_amount=Decimal('0.00'))
    
    total_orders_fixed = 0
    total_items_fixed = 0

    print(f"Found {orders.count()} historical orders that need fixing...")

    for order in orders:
        subtotal = Decimal('0.00')

        # Fix Order Items
        for item in order.items.all():
            variant = item.product_variant
            
            # Approximate the historical price based on the current product variant
            price_to_use = variant.discounted_price if variant.discounted_price and variant.discounted_price > 0 else variant.price
            
            # Save the historical item price
            item.price = price_to_use
            item.save()
            
            subtotal += price_to_use * Decimal(item.quantity)
            total_items_fixed += 1

        # Reconstruct standard cart charges
        taxes = subtotal * Decimal(os.getenv("TAX_PERCENT", '0.18'))
        
        # We only apply handling and delivery if there was a subtotal > 0
        if subtotal > Decimal('0.00'):
            handling = Decimal(os.getenv("HANDLING_CHARGE", '30.00'))
            delivery = Decimal(os.getenv("DELIVERY_CHARGE", '50.00'))
        else:
            handling = Decimal('0.00')
            delivery = Decimal('0.00')

        final_amount = subtotal + taxes + handling + delivery

        # Save to Order
        order.total_amount = subtotal
        order.taxes = taxes
        order.handling_charges = handling
        order.delivery_charges = delivery
        order.final_amount = final_amount
        order.save()
        
        total_orders_fixed += 1
        print(f"Fixed Order #{order.order_id}: Sub={subtotal}, Tax={taxes}, Final={final_amount}")

    print("\n--- FIX COMPLETE ---")
    print(f"Orders Fixed: {total_orders_fixed}")
    print(f"Items Fixed: {total_items_fixed}")

if __name__ == '__main__':
    fix_historical_orders()
