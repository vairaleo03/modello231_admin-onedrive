import google.generativeai as genai
from sqlalchemy.orm import Session
from app.models.prompts import Prompt
from app.database import SessionLocal  # dipende dal tuo setup, assicurati che sia la sessione corretta
import os
import re
from dotenv import load_dotenv

load_dotenv()
GEMINI_API=os.getenv("GEMINI_API_KEY")

def generate_summary(transcript_text: str) -> str:
    genai.configure(api_key=GEMINI_API)

    def clean_html(raw_html: str) -> str:
        return re.sub(r"<[^>]+>", "", raw_html).strip()

    # Connessione al DB per recuperare il prompt
    db: Session = SessionLocal()
    try:
        prompt_row = db.query(Prompt).filter(Prompt.id == 1).first()
        if not prompt_row:
            raise ValueError("⚠️ Prompt non trovato nel database.")

        prompt_template = prompt_row.prompt
        transcript_clean = clean_html(transcript_text)

        prompt = (
            prompt_template.strip()
            + "\n\n<TRASCRIZIONE>\n"
            + transcript_clean.strip()
            + "\n</TRASCRIZIONE>"
        )
        #prompt = prompt_template.replace("{{TRASCRIZIONE}}", transcript_text)

        # Generazione contenuto con Gemini
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        print("\n--- PROMPT ---\n")
        print(prompt)
        print("\n--- FINE PROMPT ---\n")

        print("\n--- RISPOSTA ---\n")
        print(response.text)
        print("\n--- FINE RISPOSTA ---\n")
        return response.text

    finally:
        db.close()
