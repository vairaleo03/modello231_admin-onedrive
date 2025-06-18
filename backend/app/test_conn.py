from database import engine
from sqlalchemy import text

def test_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Connessione al database riuscita:", result.fetchone())
    except Exception as e:
        print("❌ Errore di connessione:", e)

if __name__ == "__main__":
    test_connection()
