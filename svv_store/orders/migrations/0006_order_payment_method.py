from django.db import migrations, models


class Migration(migrations.Migration):
    """
    The `payment_method` column was already added to the `order` table
    by migration 0001_add_payment_method (raw ALTER TABLE ... ADD COLUMN IF NOT EXISTS).
    This migration uses SeparateDatabaseAndState to update Django's state without
    touching the database, avoiding the duplicate-column error.
    """

    dependencies = [
        ('orders', '0005_order_delivery_charges_order_final_amount_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Django state update — tells the ORM the field now exists
            state_operations=[
                migrations.AddField(
                    model_name='order',
                    name='payment_method',
                    field=models.CharField(
                        choices=[('online', 'Online'), ('cod', 'Cash on Delivery')],
                        default='online',
                        max_length=20,
                    ),
                ),
            ],
            # No actual SQL — the column is already in the DB
            database_operations=[],
        ),
    ]
