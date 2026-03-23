from django.db import migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE category ALTER COLUMN image TYPE TEXT;",
                "ALTER TABLE category ALTER COLUMN image DROP NOT NULL;",
                "ALTER TABLE sub_category ALTER COLUMN image TYPE TEXT;",
                "ALTER TABLE sub_category ALTER COLUMN image DROP NOT NULL;",
            ],
            reverse_sql=[
                "ALTER TABLE category ALTER COLUMN image TYPE VARCHAR(100) USING image::VARCHAR(100);",
                "ALTER TABLE sub_category ALTER COLUMN image TYPE VARCHAR(100) USING image::VARCHAR(100);",
            ],
        ),
    ]
