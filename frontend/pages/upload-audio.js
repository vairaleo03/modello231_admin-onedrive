import React, { useState, useEffect } from "react";
import { useRouter } from "next/router";
import styles from "../styles/upload-audio.module.css";
import { FaCheckCircle, FaCloudUploadAlt } from "react-icons/fa";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import { withAuthPage } from "../utils/auth";

export const getServerSideProps = withAuthPage(async (ctx, userId) => {
  return { props: {} };
});

const UploadPage = () => {
  const [audioFile, setAudioFile] = useState(null);
  const [audioPreview, setAudioPreview] = useState(null);
  const [audioFileId, setAudioFileId] = useState(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [messages, setMessages] = useState([]);
  const [ws, setWs] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [progress, setProgress] = useState(null);
  
  // Nuovi stati per OneDrive
  const [oneDriveStatus, setOneDriveStatus] = useState(null);

  const router = useRouter();
  
  useEffect(() => {
    const socketDomain = process.env.NEXT_PUBLIC_BE?.replace(/^https?:\/\//, "");
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  
    if (!socketDomain) {
      console.warn("⚠️ Variabile NEXT_PUBLIC_BE non definita.");
      return;
    }
  
    const socket = new WebSocket(`${protocol}://${socketDomain}/ws/notifications`);
  
    socket.onopen = () => {
      console.log("✅ Connessione WebSocket stabilita.");
    };
  
    socket.onmessage = (event) => {
      console.log("📨 Messaggio dal WebSocket:", event.data);
      try {
        const data = JSON.parse(event.data);
        if (data.type === "notification") {
          setNotifications((prev) => [...prev, data.message]);
          setTimeout(() => {
            setNotifications((prev) =>
              prev.filter((msg) => msg !== data.message)
            );
          }, 5000);
        } else if (data.type === "progress") {
          setProgress(data.message);
        }
      } catch (error) {
        console.error("⚠️ Errore nel parsing del messaggio WebSocket:", error);
      }
    };
  
    socket.onerror = (error) => {
      console.error("❌ Errore WebSocket:", error);
    };
  
    socket.onclose = () => {
      console.log("🔌 Connessione WebSocket chiusa.");
    };
  
    return () => {
      if (socket.readyState === WebSocket.OPEN) {
        console.log("🔒 Chiudo WebSocket...");
        socket.close();
      }
    };
  }, []);

  // Gestisce il caricamento automatico del file audio - RIMOSSO PARAMETRO ONEDRIVE
  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) {
      setAudioFile(file);
      setAudioFileId(null);
      setAudioPreview(URL.createObjectURL(file));
      setOneDriveStatus(null);
      setProgress("Salvataggio audio...");
      await handleUpload(file);
    }
  };
  
  const handleUpload = async (file) => {
    if (!file) {
      alert("Seleziona un file audio prima di caricare.");
      return;
    }
  
    const formData = new FormData();
    formData.append("audio_file", file);
  
    // RIMOSSO: Parametro save_to_onedrive
    const uploadUrl = `${process.env.NEXT_PUBLIC_BE}/audio/upload`;
  
    try {
      const response = await fetch(uploadUrl, {
        method: "POST",
        body: formData,
      });
  
      if (response.ok) {
        const data = await response.json();
        setAudioFileId(data.audio_file_id);
        setProgress(null);
        
        // RIMOSSO: Gestione automatica OneDrive
      } else {
        alert("Errore durante il caricamento del file.");
        setProgress(null);
      }
    } catch (error) {
      console.error("Errore:", error);
      alert("Errore di rete durante il caricamento del file.");
      setProgress(null);
    }
  };

  // Funzione per salvare file esistente su OneDrive
  const saveExistingToOneDrive = async () => {
    if (!audioFileId) {
      alert("Nessun file da salvare su OneDrive.");
      return;
    }

    setProgress("Salvataggio su OneDrive...");

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BE}/audio/${audioFileId}/save-onedrive`,
        { method: "POST" }
      );

      if (response.ok) {
        const result = await response.json();
        setOneDriveStatus({
          saved: true,
          file_id: result.file_info.file_id,
          filename: result.file_info.filename,
          folder_path: result.file_info.folder_path,
          web_url: result.file_info.web_url
        });
      } else {
        const errorData = await response.json();
        setOneDriveStatus({
          saved: false,
          error: errorData.detail || "Errore nel salvataggio"
        });
      }
    } catch (error) {
      console.error("Errore OneDrive:", error);
      setOneDriveStatus({
        saved: false,
        error: "Errore di connessione"
      });
    } finally {
      setProgress(null);
    }
  };

  // Invia una richiesta al backend per avviare la trascrizione
  const handleStartTranscription = async () => {
    if (!audioFileId) {
      alert("ID del file audio non trovato.");
      return;
    }
  
    setIsTranscribing(true);
  
    const fetchPromise = fetch(
      `${process.env.NEXT_PUBLIC_BE}/start-transcription/${audioFileId}`,
      {
        method: "POST",
      }
    );
  
    setProgress("Converto il formato per un'ottima compatibilità...");
    await new Promise((resolve) => setTimeout(resolve, 3000));
  
    setProgress("Divido l'audio in segmenti...");
    await new Promise((resolve) => setTimeout(resolve, 3000));
  
    setProgress("Effettuo la trascrizione...");
  
    try {
      const response = await fetchPromise;
  
      if (response.ok) {
        const data = await response.json();
        setProgress("Reindirizzo alla pagina editor...");
  
        setTimeout(() => {
          router.push(`/transcription-editor?transcript_id=${data.transcript_id}`);
        }, 2500);
      } else {
        const errorData = await response.json();
        console.error("Errore backend: ", errorData.detail);
        alert(`Errore durante l'avvio della trascrizione: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Errore:", error);
      alert("Errore di rete durante l'avvio della trascrizione.");
      setIsTranscribing(false);
    }
  };

  return (
    <>
      {notifications.map((message, index) => (
        <div key={index} className={styles.notification}>
          <FaCheckCircle className={styles.successIcon} /> {message}
        </div>
      ))}

      {/* Status OneDrive */}
      {oneDriveStatus && (
        <div className={`${styles.notification} ${oneDriveStatus.saved ? styles.success : styles.error}`}>
          {oneDriveStatus.saved ? (
            <>
              <FaCheckCircle className={styles.successIcon} />
              File audio salvato su OneDrive
              <div className={styles.fileInfo}>
                📄 {oneDriveStatus.filename}
                {oneDriveStatus.web_url && (
                  <a href={oneDriveStatus.web_url} target="_blank" rel="noopener noreferrer" className={styles.viewLink}>
                    Visualizza
                  </a>
                )}
              </div>
            </>
          ) : (
            <>
              <span className={styles.errorIcon}>❌</span>
              Errore OneDrive: {oneDriveStatus.error}
            </>
          )}
        </div>
      )}

      <div className={styles.modalContainer}>
        {!audioPreview && (
          <div className={styles.uploadContainer}>
            <h1 className={styles.uploadTitle}>Carica un file audio</h1>
            
            {/* RIMOSSO: Checkbox OneDrive automatico */}

            <input
              type="file"
              accept="audio/*"
              onChange={handleFileChange}
              className={styles.hiddenInput}
              id="fileInput"
            />
            <label htmlFor="fileInput" className={styles.uploadButton}>
              Seleziona
            </label>
          </div>
        )}

        {audioPreview && (
          <div className={styles.modalPreview}>
            <h2>{audioFile?.name}</h2>
            <audio controls>
              <source src={audioPreview} type="audio/mpeg" />
              Il tuo browser non supporta l&apos;elemento audio.
            </audio>

            {/* Mostra status OneDrive se disponibile */}
            {oneDriveStatus && (
              <div className={styles.oneDriveStatus}>
                {oneDriveStatus.saved ? (
                  <div className={styles.oneDriveSuccess}>
                    <FaCloudUploadAlt /> Salvato su OneDrive: {oneDriveStatus.filename}
                  </div>
                ) : (
                  <div className={styles.oneDriveError}>
                    ❌ Errore OneDrive: {oneDriveStatus.error}
                  </div>
                )}
              </div>
            )}

            <div className={styles.buttons}>
              <button
                className={`${styles.button} ${(!audioFileId || isTranscribing) ? styles.disabled : ""}`}
                onClick={handleStartTranscription}
                disabled={isTranscribing || !audioFileId}
              >
                {isTranscribing ? "Trascrizione in corso..." : "Avvia Trascrizione"}
              </button>

              {/* Bottone per salvare su OneDrive - SOLO MANUALE */}
              {audioFileId && (!oneDriveStatus || !oneDriveStatus.saved) && (
                <button
                  className={`${styles.button} ${styles.onedriveButton}`}
                  onClick={saveExistingToOneDrive}
                  disabled={progress !== null}
                >
                  <FaCloudUploadAlt />
                  Salva su OneDrive
                </button>
              )}

              <button
                className={`${styles.button} ${styles.secondary}`}
                onClick={() => {
                  setAudioPreview(null);
                  setOneDriveStatus(null);
                }}
              >
                Chiudi
              </button>
            </div>
          </div>
        )}

        {/* Banner di progresso */}
        {progress !== null && (
          <div className={styles.progressModal}>
            <AiOutlineLoading3Quarters className={styles.spinner} /> {progress}
          </div>
        )}
      </div>
    </>
  );
};

export default UploadPage;