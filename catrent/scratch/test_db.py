import os
import psycopg2
from pathlib import Path

def _load_env_file(env_path):
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value

def test_connection():
    base_dir = Path(__file__).resolve().parent.parent
    _load_env_file(base_dir / '.env')
    db_url = os.getenv('DATABASE_URL')
    print(f"Testing connection to: {db_url}")
    try:
        conn = psycopg2.connect(db_url)
        print("Connection successful!")
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print(f"DB Version: {cur.fetchone()}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
