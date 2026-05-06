from django.db import migrations


class Migration(migrations.Migration):
    """
    Manual merge migration to resolve conflicting leaf nodes:
      - categories/0001_initial  (original tree, March 2026)
      - categories/0003_initial  (new tree via 0001_alter_image_to_base64, April 2026)

    Both trees were applied to the database independently. This migration
    declares both as dependencies so Django sees a single leaf node and
    migration conflicts are resolved.

    No schema operations are performed — this is a bookkeeping-only migration.
    """

    dependencies = [
        ('categories', '0001_initial'),
        ('categories', '0003_initial'),
    ]

    operations = [
        # No operations — this is a merge-only migration
    ]
