"""
Standalone script to apply the image -> base64 migration.

Run from the svv_store directory:
    python apply_image_migration.py

What it does:
  1. Reads DB credentials from .env
  2. Alters image columns in category, sub_category, product_image to TEXT + nullable
  3. Records the migrations in django_migrations so Django tracks them
"""

import os
import sys

# ---------------------------------------------------------------------------
# Read .env
# ---------------------------------------------------------------------------
env_path = os.path.join(os.path.dirname(__file__), '.env')

if not os.path.exists(env_path):
    print(f"ERROR: .env file not found at {env_path}")
    sys.exit(1)

env = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        env[key.strip()] = value.strip().strip("'\"")

DB_NAME = env.get('DB_NAME')
DB_USER = env.get('DB_USER')
DB_PASSWORD = env.get('DB_PASSWORD')
DB_HOST = env.get('DB_HOST', 'localhost')
DB_PORT = env.get('DB_PORT', '5432')

if not all([DB_NAME, DB_USER, DB_PASSWORD]):
    print("ERROR: Missing DB_NAME, DB_USER or DB_PASSWORD in .env")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------
try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER} ...")

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
)
conn.autocommit = False
cur = conn.cursor()

# ---------------------------------------------------------------------------
# SQL changes
# ---------------------------------------------------------------------------
alter_statements = [
    # category
    ("ALTER TABLE category ALTER COLUMN image TYPE TEXT",              "category.image -> TEXT"),
    ("ALTER TABLE category ALTER COLUMN image DROP NOT NULL",          "category.image -> nullable"),
    # sub_category
    ("ALTER TABLE sub_category ALTER COLUMN image TYPE TEXT",          "sub_category.image -> TEXT"),
    ("ALTER TABLE sub_category ALTER COLUMN image DROP NOT NULL",      "sub_category.image -> nullable"),
    # product_image
    ("ALTER TABLE product_image ALTER COLUMN image TYPE TEXT",         "product_image.image -> TEXT"),
    ("ALTER TABLE product_image ALTER COLUMN image DROP NOT NULL",     "product_image.image -> nullable"),
]

print("\nApplying schema changes ...")
for sql, label in alter_statements:
    try:
        cur.execute(sql)
        print(f"  OK  {label}")
    except Exception as e:
        # Column may already be TEXT / already nullable — treat as warning
        print(f"  SKIP {label}: {e}".replace('\n', ' '))
        conn.rollback()
        conn.autocommit = False

# ---------------------------------------------------------------------------
# Ensure django_migrations table exists
# ---------------------------------------------------------------------------
cur.execute("""
    CREATE TABLE IF NOT EXISTS django_migrations (
        id SERIAL PRIMARY KEY,
        app VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL,
        applied TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )
""")

# ---------------------------------------------------------------------------
# Record migrations (skip if already recorded)
# ---------------------------------------------------------------------------
migrations_to_record = [
    ('categories', '0001_alter_image_to_base64'),
    ('products',   '0001_alter_image_to_base64'),
]

print("\nRecording migrations in django_migrations ...")
for app, name in migrations_to_record:
    cur.execute(
        "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s",
        (app, name)
    )
    if cur.fetchone():
        print(f"  SKIP {app}.{name} (already recorded)")
    else:
        cur.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
            (app, name)
        )
        print(f"  OK   {app}.{name}")

conn.commit()
cur.close()
conn.close()

print("\nDone! Migration applied successfully.")
