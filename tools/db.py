import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def save_transcription(raw_text, formatted_text, mode="plain"):
    """
    Saves the transcription log into the Supabase PostgreSQL database.
    """
    if not DATABASE_URL:
        return
        
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        insert_query = """
        INSERT INTO transcriptions (raw_transcription, formatted_transcription, formatting_mode)
        VALUES (%s, %s, %s)
        """
        
        cur.execute(insert_query, (raw_text, formatted_text, mode))
        conn.commit()
        
        cur.close()
        conn.close()
        print("💽 Saved run to database log.")
        
    except Exception as e:
        print(f"❌ Failed to save to database: {e}")

if __name__ == "__main__":
    save_transcription("testing raw", "Testing raw.", "plain")
