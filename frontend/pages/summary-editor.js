import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import "prosemirror-view/style/prosemirror.css";
import styles from "../styles/transcription-editor.module.css";
import { FaCheckCircle, FaCloudUploadAlt, FaDownload } from "react-icons/fa";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import Toolbar from "../components/Editor-toolbar";
import Modal from "react-modal";
import modalStyles from "../styles/modal.module.css";
import { withAuthPage } from "../utils/auth";

export const getServerSideProps = withAuthPage(async (ctx, userId) => {
  return { props: {} };
});

const SummaryEditor = () => {
  const router = useRouter();
  const { summary_id } = router.query;
  const [content, setContent] = useState("");
  const [isMounted, setIsMounted] = useState(false);
  const [debounceTimeout, setDebounceTimeout] = useState(null);
  const [socket, setSocket] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [progress, setProgress] = useState(null);

  const [showDownloadModal, setShowDownloadModal] = useState(false);
  const [formData, setFormData] = useState({
    VERIFICA: "ordinaria",
    NUMERO_VERBALE: 1,
    LUOGO_RIUNIONE: "Call Conference",
    DATA_RIUNIONE: new Date().toISOString().split("T")[0],
    ORARIO_INIZIO: "17:00",
    ORARIO_FINE: "18:00",
  });

  // Nuovi stati per OneDrive
  const [isUploadingOneDrive, setIsUploadingOneDrive] = useState(false);
  const [isUploadingFormattedOneDrive, setIsUploadingFormattedOneDrive] = useState(false);
  const [oneDriveStatus, setOneDriveStatus] = useState(null);
  const [showOneDriveModal, setShowOneDriveModal] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleDownload = async (action = "download") => {
    await saveSummary(content);
    setTimeout(async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_BE}/summary/${summary_id}/word?action=${action}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData),
          }
        );
        
        if (response.ok) {
          if (action === "download") {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `verbale_${summary_id}.docx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            setShowDownloadModal(false);
          } else if (action === "onedrive") {
            const result = await response.json();
            setOneDriveStatus({
              success: true,
              message: result.message,
              fileInfo: result.file_info
            });
            setShowOneDriveModal(false);
          }
        } else {
          const errorData = await response.json();
          if (action === "onedrive") {
            setOneDriveStatus({
              success: false,
              message: errorData.detail || "Errore nel salvataggio"
            });
          }
        }
      } catch (err) {
        console.error("Errore nel download del riassunto Word", err);
        if (action === "onedrive") {
          setOneDriveStatus({
            success: false,
            message: "Errore di connessione"
          });
        }
      }
    }, 1000);
  };

  // Nuova funzione per salvare il verbale formattato su OneDrive
  const saveFormattedToOneDrive = async () => {
    setIsUploadingFormattedOneDrive(true);
    await saveSummary(content);
    
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BE}/summary/${summary_id}/save-formatted-onedrive`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(formData),
        }
      );

      if (response.ok) {
        const result = await response.json();
        setOneDriveStatus({
          success: true,
          message: result.message,
          fileInfo: result.file_info
        });
        setShowOneDriveModal(false);
      } else {
        const errorData = await response.json();
        setOneDriveStatus({
          success: false,
          message: errorData.detail || "Errore nel salvataggio"
        });
      }
    } catch (error) {
      console.error("Errore OneDrive:", error);
      setOneDriveStatus({
        success: false,
        message: "Errore di connessione"
      });
    } finally {
      setIsUploadingFormattedOneDrive(false);
    }
  };

  // Funzione per salvare il verbale semplice su OneDrive
  const saveToOneDrive = async () => {
    setIsUploadingOneDrive(true);
    setOneDriveStatus(null);

    try {
      await saveSummary(content);
      
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BE}/summary/${summary_id}/save-onedrive`,
        { method: "POST" }
      );

      if (response.ok) {
        const result = await response.json();
        setOneDriveStatus({
          success: true,
          message: result.message,
          fileInfo: result.file_info
        });
      } else {
        const errorData = await response.json();
        setOneDriveStatus({
          success: false,
          message: errorData.detail || "Errore nel salvataggio"
        });
      }
    } catch (error) {
      console.error("Errore OneDrive:", error);
      setOneDriveStatus({
        success: false,
        message: "Errore di connessione"
      });
    } finally {
      setIsUploadingOneDrive(false);
    }
  };

  useEffect(() => {
    Modal.setAppElement("#__next");
    setIsMounted(true);
    const socketDomain = process.env.NEXT_PUBLIC_BE?.replace(/^https?:\/\//, "");
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${socketDomain}/ws/notifications`);
    
    ws.onopen = () => {
      console.log("WebSocket connesso per aggiornamenti di salvataggio");
    };
    
    ws.onmessage = (event) => {
      console.log("Messaggio dal WebSocket:", event.data);
      const data = JSON.parse(event.data);
      if (data.type === "notification") {
        setNotifications((prev) => [...prev, data.message]);
        setTimeout(() => {
          setNotifications((prev) =>
            prev.filter((msg) => msg !== data.message)
          );
        }, 2500);
      } else if (data.type === "progress") {
        setProgress(data.message);
      }
    };
    
    ws.onerror = (error) => {
      console.error("Errore WebSocket:", error);
    };
    
    ws.onclose = () => {
      console.log("Connessione WebSocket chiusa.");
    };
    
    setSocket(ws);

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        console.log("Chiudendo WebSocket...");
        ws.close();
      }
    };
  }, []);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        hardBreak: true,
      }),
      Underline,
    ],
    content: "",
    onUpdate: ({ editor }) => {
      const newContent = editor.getHTML();
      setContent(newContent);
      handleDebouncedSave(newContent);
    },
    editorProps: {
      attributes: {
        class: `${styles.editorContainer}`,
        style: "white-space: pre-wrap;",
      },
    },
    injectCSS: false,
    editable: true,
    immediatelyRender: false,
  });

  const handleDebouncedSave = (newContent) => {
    if (debounceTimeout) clearTimeout(debounceTimeout);
    const timeout = setTimeout(() => saveSummary(newContent), 4000);
    setDebounceTimeout(timeout);
  };

  const saveSummary = async (summary) => {
    if (!summary_id) return;
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_BE}/summary/${summary_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ summary_text: summary }),
      });
      if (response.ok) {
        console.log('Trascrizione aggiornata correttamente');
      } else {
        console.error('Errore durante il salvataggio della trascrizione');
      }
    } catch (error) {
      console.error('Errore di rete: ', error);
    }
  };

  useEffect(() => {
    const fetchSummary = async () => {
      if (!summary_id) return;
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_BE}/summary/${summary_id}`
        );
        if (response.ok) {
          const data = await response.json();
          if (data.summary_text) {
            editor?.commands.setContent(data.summary_text);
            setContent(data.summary_text);
          }
        } else {
          console.error("Errore nel recupero del riassunto");
        }
      } catch (error) {
        console.error("Errore di rete: ", error);
      }
    };
    if (isMounted) {
      fetchSummary();
    }
  }, [summary_id, editor, isMounted]);

  if (!isMounted) return null;

  return (
    <>
      {notifications.map((message, index) => (
        <div key={index} className={styles.notification}>
          <FaCheckCircle className={styles.successIcon} /> {message}
        </div>
      ))}

      {/* Status OneDrive */}
      {oneDriveStatus && (
        <div className={`${styles.notification} ${oneDriveStatus.success ? styles.success : styles.error}`}>
          {oneDriveStatus.success ? (
            <FaCheckCircle className={styles.successIcon} />
          ) : (
            <span className={styles.errorIcon}>❌</span>
          )}
          {oneDriveStatus.message}
          {oneDriveStatus.fileInfo && (
            <div className={styles.fileInfo}>
              📄 {oneDriveStatus.fileInfo.filename}
            </div>
          )}
        </div>
      )}

      <div className={styles.editorWrapper}>
        <div className={styles.toolbarWrapper}>
          <Toolbar editor={editor} />
          <button
            onClick={() => setShowDownloadModal(true)}
            className={styles.saveButton}
          >
            <FaDownload />
            Scarica verbale
          </button>
        </div>
        
        <div className={styles.editorBox}>
          <EditorContent editor={editor} />
        </div>
        
        <div className={styles.buttonsContainer}>
          <button
            onClick={() => setShowDownloadModal(true)}
            className={styles.saveButton}
          >
            <FaDownload />
            Scarica verbale
          </button>

          <button
            onClick={() => setShowOneDriveModal(true)}
            className={`${styles.saveButton} ${styles.onedriveButton}`}
          >
            <FaCloudUploadAlt />
            Salva verbale su OneDrive
          </button>

          <button
            onClick={saveToOneDrive}
            className={`${styles.saveButton} ${styles.onedriveButton} ${
              isUploadingOneDrive ? styles.disabled : ""
            }`}
            disabled={isUploadingOneDrive}
          >
            {isUploadingOneDrive ? (
              <AiOutlineLoading3Quarters className={styles.spinner} />
            ) : (
              <FaCloudUploadAlt />
            )}
            {isUploadingOneDrive ? "Caricamento..." : "Salva testo su OneDrive"}
          </button>
        </div>

        {/* Modal Download */}
        <Modal
          isOpen={showDownloadModal}
          onRequestClose={() => setShowDownloadModal(false)}
          contentLabel="Compila dati verbale"
          className={modalStyles.modalContent}
          overlayClassName={modalStyles.modalOverlay}
        >
          <h2 className={modalStyles.title}>Impostazioni Verbale</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleDownload("download");
            }}
            className={modalStyles.form}
          >
            <div className={modalStyles.formGroup}>
              <label>Verifica</label>
              <select
                name="VERIFICA"
                value={formData.VERIFICA}
                onChange={handleChange}
                className={modalStyles.input}
              >
                <option value="ordinaria">Ordinaria</option>
                <option value="straordinaria">Straordinaria</option>
              </select>
            </div>

            <div className={modalStyles.formGroup}>
              <label>Numero Verbale</label>
              <input
                type="number"
                name="NUMERO_VERBALE"
                value={formData.NUMERO_VERBALE}
                onChange={handleChange}
                className={modalStyles.input}
              />
            </div>

            <div className={modalStyles.formGroup}>
              <label>Luogo Riunione</label>
              <input
                type="text"
                name="LUOGO_RIUNIONE"
                value={formData.LUOGO_RIUNIONE}
                onChange={handleChange}
                className={modalStyles.input}
              />
            </div>

            <div className={modalStyles.formGroup}>
              <label>Data Riunione</label>
              <input
                type="date"
                name="DATA_RIUNIONE"
                value={formData.DATA_RIUNIONE}
                onChange={handleChange}
                className={modalStyles.input}
              />
            </div>

            <div className={modalStyles.flexRow}>
              <div className={modalStyles.formGroup}>
                <label>Orario Inizio</label>
                <input
                  type="time"
                  name="ORARIO_INIZIO"
                  value={formData.ORARIO_INIZIO}
                  onChange={handleChange}
                  className={modalStyles.input}
                />
              </div>
              <div className={modalStyles.formGroup}>
                <label>Orario Fine</label>
                <input
                  type="time"
                  name="ORARIO_FINE"
                  value={formData.ORARIO_FINE}
                  onChange={handleChange}
                  className={modalStyles.input}
                />
              </div>
            </div>

            <div className={modalStyles.actionsCenter}>
              <button type="submit" className={modalStyles.submitButton}>
                <FaDownload /> Scarica
              </button>
            </div>
          </form>
        </Modal>

        {/* Modal OneDrive */}
        <Modal
          isOpen={showOneDriveModal}
          onRequestClose={() => setShowOneDriveModal(false)}
          contentLabel="Salva su OneDrive"
          className={modalStyles.modalContent}
          overlayClassName={modalStyles.modalOverlay}
        >
          <h2 className={modalStyles.title}>Salva Verbale su OneDrive</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              saveFormattedToOneDrive();
            }}
            className={modalStyles.form}
          >
            <div className={modalStyles.formGroup}>
              <label>Verifica</label>
              <select
                name="VERIFICA"
                value={formData.VERIFICA}
                onChange={handleChange}
                className={modalStyles.input}
              >
                <option value="ordinaria">Ordinaria</option>
                <option value="straordinaria">Straordinaria</option>
              </select>
            </div>

            <div className={modalStyles.formGroup}>
              <label>Numero Verbale</label>
              <input
                type="number"
                name="NUMERO_VERBALE"
                value={formData.NUMERO_VERBALE}
                onChange={handleChange}
                className={modalStyles.input}
              />
            </div>

            <div className={modalStyles.formGroup}>
              <label>Luogo Riunione</label>
              <input
                type="text"
                name="LUOGO_RIUNIONE"
                value={formData.LUOGO_RIUNIONE}
                onChange={handleChange}
                className={modalStyles.input}
              />
            </div>

            <div className={modalStyles.formGroup}>
              <label>Data Riunione</label>
              <input
                type="date"
                name="DATA_RIUNIONE"
                value={formData.DATA_RIUNIONE}
                onChange={handleChange}
                className={modalStyles.input}
              />
            </div>

            <div className={modalStyles.flexRow}>
              <div className={modalStyles.formGroup}>
                <label>Orario Inizio</label>
                <input
                  type="time"
                  name="ORARIO_INIZIO"
                  value={formData.ORARIO_INIZIO}
                  onChange={handleChange}
                  className={modalStyles.input}
                />
              </div>
              <div className={modalStyles.formGroup}>
                <label>Orario Fine</label>
                <input
                  type="time"
                  name="ORARIO_FINE"
                  value={formData.ORARIO_FINE}
                  onChange={handleChange}
                  className={modalStyles.input}
                />
              </div>
            </div>

            <div className={modalStyles.actionsCenter}>
              <button 
                type="submit" 
                className={modalStyles.submitButton}
                disabled={isUploadingFormattedOneDrive}
              >
                {isUploadingFormattedOneDrive ? (
                  <AiOutlineLoading3Quarters className={styles.spinner} />
                ) : (
                  <FaCloudUploadAlt />
                )}
                {isUploadingFormattedOneDrive ? "Caricamento..." : "Salva su OneDrive"}
              </button>
            </div>
          </form>
        </Modal>
      </div>
    </>
  );
};

export default SummaryEditor;
