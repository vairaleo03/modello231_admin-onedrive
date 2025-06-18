from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_summary(transcript_text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages = [
            {
                "role": "system",
                "content": (
                    "Sei un legale esperto incaricato della redazione di verbali formali per l'Organismo di Vigilanza (OdV), "
                    "in conformità al D.Lgs. 231/2001. Devi redigere un verbale giuridicamente corretto, ispezionabile e archiviabile, "
                    "sulla base di una trascrizione integrale di una riunione, usando il modello di riferimento ufficiale."
                    "Devi utilizzare un liguaggio altamente giuridico e professionale."
                )
            },
            {
                "role": "user",
                "content": (
                    "Modello da seguire:\n\n"
                    "1. Oggetto della riunione: \n"
                    "(Inserisci in modo sintetico se si tratta di una verifica ordinaria o straordinaria, relativa al processo dedotto dalla trascrizione fornita)\n"
                    "ESEMPIO: Verifica ordinaria relativa al processo commerciale e gare\n\n"
                    "2. Processo interessato dal controllo dell’OdV: \n"
                    "(Inserisci il processo sul quale si basa il controllo dell'organismo di vigilanza, deduci il processo aziendale dalla trascrizione fornita) \n"
                    "ESEMPIO: Processo commerciale e gare (P.4 MOG) \n\n"
                    "3. Documenti esaminati\n"
                    "(Deduci dalla trascrizione fornita, quali documenti sono stati esaminati nel corso della riunione trascritta, ed elenca tali documenti)\n"
                    "ESEMPIO: a) Richiesta del comune di Tria del 26.02.2025 b) Nota C.N.S. del 20.02.2025 + Riscontro della san giovanni di dio del 26.02.2025 c) nota comune di putignano del 24.01.2025 d)Elenco servizi in essere con le relative specifiche. \n\n"
                    "4. Descrizione delle attività condotte:\n"
                    "(Fornisci una descrizione dettagliata e discorsiva riguardo le attività condotte durante la riunione trascritta. Dividi la descrizione delle attività in - Premessa - Argomenti trattati)\n"
                    "   4.1 Premessa\n"
                    "   (Fornisci una premessa dettagliata e discorsiva, che introduce gli argomenti trattati durante la riunione trascritta)\n"
                    "   ESEMPIO: Il presidente introduce la riunione informando i presenti in ordine alle attività di verifica che verranno odiernamente poste in essere, specificandone finalità e modalità. A tal proposito, viene precisato che verranno condotte specifiche verifiche .... \n"
                    "   4.2 Argomenti trattati\n"
                    "   (Questa è la sezione in cui viene riassunto nel dettaglio tutto l'incontro. Fornisci una descrizione lunga, dettagliata e discorsiva degli argomenti trattati durante la riunione trascritta, fornisci un resoconto degli argomenti emersi nella trascrizione e fornisci una spiegazione dettagliata e professionale con linguaggio altamente giuridico e formale)\n"
                    "   ESEMPIO: Con riferimento all'argomento posto all'ordine del giorno, l'odv incontra il Dott.Giuseppe Raimondi (Responsabile ufficio Gare della Cooperativa) per eseminare il processo commerciale e gare (P.4 MOG) e raccogliere le relative evidenze documentali. Innanzitutto, l'odv prende atto che per l'anno 2025 l'ente non ha partecipato a nuove gare a causa del recente provvediamento del 4.12.2024, con il quale la prefettura UTG di Foggia ha adottato un'informazione interdittiva ex art.84 e 91 del d.lgs. n. 159/2011 nei confronti dell'ente e del contestuale provvedimento di nomina dei commissionari per l'esecuzione.... \n\n"
                    "5. Considerazioni\n"
                    "(Fornisci delle considerazione sulla corretta attuazione del modello 231, e fornisci in modo chiaro e dettagliato le criticità emerse rispetto al modello 231 in termini di etica ecc.)\n"
                    "ESEMPIO: Al termine dell'odierna sessione l'odv ha potuto rilevare - allo stato e sulla base delle informazioni fornite, oltre che di quelle ricavabili dalla documentazione consultata - i seguenti aspetti: a) Per quanto è stato possibile verificare, nell'attuazione dei protocolli del modello 231, processo commerciale e gare (P.4 MOG): - non si rivelano criticità, fatti salvi gli effetti dell'informaizone interdittiva sopra citata ampiamente affrontati nel corso della riunione odierna. ....... \n\n"
                    "6. Conclusioni\n\n"
                    "(Fornisci le conclusioni rispetto il controllo effettuato durante l'incontro trascritto. Fornisci un ricapitolato di quanto discusso e gli esiti dell'incontro)\n"
                    "ESEMPIO: Al termine della propria riunione, con riferimento alle circostanze apprese nel corso della verifica, della documentazione esaminata, delle informazioni acquisite, nonché dalle valutazioni condotte e sopra rappresentate, l’OdV – in attuazione dei propri poteri di iniziativa, vigilanza e controllo – tenuto conto degli esiti della verifica invita la Cooperativa: A continuare a mantenere elevato il livello di attenzione sull’osservanza del Modello 231 vigente; b) Ad informare tempestivamente l’OdV in ordine a qualunque anomalia o criticità che dovesse verificarsi in merito al rispetto del Modello da parte di coloro che sono tenuti ad osservarne le disposizioni; c)A continuare a garantire costanza ai controlli interni sulle attività e processi a rischio.\n\n"
                    "Indicazioni importanti e obbligatorie da seguire:\n"
                    "- In ogni sezione includi tutti i dettagli rilevanti: nomi (es. Dott. Raimondi, Francesco Casiello), date (es. 26.02.2025), norme (es. art. 84 D.lgs. 159/2011), documenti, sedi e incarichi.\n"
                    "- Descrivi gli interventi in modo narrativo, come in un verbale OdV autentico: es. “Il Responsabile Ufficio Gare comunica...”, “La Cooperativa ha risposto con nota del...”, “L’OdV prende atto...”\n"
                    "- Usa linguaggio giuridico-amministrativo: non usare frasi vaghe o riassuntive. Ogni fatto rilevante deve essere riportato.\n"
                    "Fai un bel respiro e procedi a dare il massimo. Restituiscimi l'output con tag html."
                )
            },
            {
                "role": "user",
                "content": f"TRASCRIZIONE:\n\n{transcript_text}"
            }
        ],
        temperature=0.3,
        max_tokens=4096
    )

    return response.choices[0].message.content.strip()
