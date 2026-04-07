from django.db import migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE \"order\" ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20) NOT NULL DEFAULT 'online';",
            reverse_sql="ALTER TABLE \"order\" DROP COLUMN IF EXISTS payment_method;",
        ),
    ]
