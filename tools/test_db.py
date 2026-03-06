import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def test_database():
    print("Testing PostgreSQL Database connection...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT version();")
        record = cur.fetchone()
        print("✅ Successfully connected to Supabase PostgreSQL!")
        
        print("\nEnsuring transcriptions table exists...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
          raw_transcription TEXT NOT NULL,
          formatted_transcription TEXT NOT NULL,
          formatting_mode VARCHAR(50) DEFAULT 'plain'
        );
        """)
        conn.commit()
        print("✅ Database schema initialized/verified.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Failed to connect to or initialize the database: {e}")

if __name__ == "__main__":
    if not DATABASE_URL or DATABASE_URL.strip() == "":
        print("❌ DATABASE_URL is not set in .env")
    else:
        test_database()
