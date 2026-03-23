from django.db import migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE product_image ALTER COLUMN image TYPE TEXT;",
                "ALTER TABLE product_image ALTER COLUMN image DROP NOT NULL;",
            ],
            reverse_sql=[
                "ALTER TABLE product_image ALTER COLUMN image SET NOT NULL;",
                "ALTER TABLE product_image ALTER COLUMN image TYPE VARCHAR(100) USING image::VARCHAR(100);",
            ],
        ),
    ]
