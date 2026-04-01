import os
import psycopg2
from dotenv import load_dotenv
from tools.output import emit_stdout

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def save_transcription(raw_text, formatted_text, mode="plain", duration=0, telemetry=None):
    """
    Saves the transcription log into the Supabase PostgreSQL database.
    Now includes duration and word_count for analytics.
    """
    if telemetry:
        telemetry.mark("database_save_start", mode=mode, duration_seconds=duration)

    if not DATABASE_URL:
        if telemetry:
            telemetry.mark("database_save_end", status="skipped_no_database_url")
        return
        
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Calculate word count (from formatted text)
        word_count = len(formatted_text.split())
        
        insert_query = """
        INSERT INTO transcriptions (raw_transcription, formatted_transcription, formatting_mode, duration, word_count)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        cur.execute(insert_query, (raw_text, formatted_text, mode, duration, word_count))
        conn.commit()
        
        cur.close()
        conn.close()
        if telemetry:
            telemetry.mark("database_save_end", status="success", word_count=word_count)
        emit_stdout("💽 Saved run to database log.")
        
    except Exception as e:
        if telemetry:
            telemetry.mark("database_save_end", status="exception", error=str(e))
        emit_stdout(f"❌ Failed to save to database: {e}")

def get_stats():
    """
    Retrieves analytics: Streak, total words, and average WPM.
    """
    if not DATABASE_URL:
        return {"streak": 0, "total_words": 0, "wpm": 0}
        
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 1. Total Words
        cur.execute("SELECT SUM(word_count) FROM transcriptions")
        total_words = cur.fetchone()[0] or 0
        
        # 2. Average WPM (Total Words / Total Minutes)
        cur.execute("SELECT SUM(word_count), SUM(duration) FROM transcriptions WHERE duration > 0")
        res = cur.fetchone()
        words_for_wpm = res[0] or 0
        total_duration_sec = res[1] or 0
        
        avg_wpm = 0
        if total_duration_sec > 0:
            avg_wpm = int((words_for_wpm / total_duration_sec) * 60)
            
        # 3. Streak (Simplified: consecutive days of activity)
        # We'll count unique dates in descending order and see how many consecutive ones we have including today
        cur.execute("""
            WITH daily_activity AS (
                SELECT DISTINCT DATE(created_at AT TIME ZONE 'UTC') as activity_date
                FROM transcriptions
                ORDER BY activity_date DESC
            )
            SELECT activity_date FROM daily_activity
        """)
        dates = [r[0] for r in cur.fetchall()]
        
        streak = 0
        if dates:
            from datetime import date, timedelta
            today = date.today()
            current_check = today
            
            # If the most recent date is not today or yesterday, streak is 0
            if dates[0] < today - timedelta(days=1):
                streak = 0
            else:
                # If the last activity was yesterday, streak continues from there
                # If it was today, streak continues from today
                if dates[0] == today or dates[0] == today - timedelta(days=1):
                    streak = 0
                    check_date = dates[0]
                    for d in dates:
                        if d == check_date:
                            streak += 1
                            check_date -= timedelta(days=1)
                        else:
                            break
        
        cur.close()
        conn.close()
        
        return {
            "streak": streak,
            "total_words": int(total_words),
            "wpm": avg_wpm
        }
    except Exception as e:
        emit_stdout(f"❌ Failed to fetch stats: {e}")
        return {"streak": 0, "total_words": 0, "wpm": 0}

if __name__ == "__main__":
    # Test stats
    print(get_stats())
