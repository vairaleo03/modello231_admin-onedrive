import React, { useState, useEffect } from "react";
import { FaArrowLeft, FaUpload, FaFileAlt, FaTimes, FaRobot, FaCheckCircle } from "react-icons/fa";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import styles from "../styles/admin-forms.module.css";

const AdminClientForm = ({ onBack }) => {
  const [formData, setFormData] = useState({
    ragioneSociale: "",
    partitaIva: "",
    codiceFiscale: "",
    telefono: "",
    email: "",
    pec: "",
    indirizzo: "",
    citta: "",
    cap: "",
    provincia: "",
    rappresentanteLegale: "",
    cfRappresentante: "",
    settoreAttivita: "",
    numeroDipendenti: "",
    note: ""
  });

  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionResults, setExtractionResults] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [socket, setSocket] = useState(null);

  const BE = process.env.NEXT_PUBLIC_BE;

  // WebSocket per notifiche
  useEffect(() => {
    const socketDomain = BE?.replace(/^https?:\/\//, "");
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${socketDomain}/ws/notifications`);
    
    ws.onopen = () => console.log("WebSocket connesso per form cliente");
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "notification") {
        setNotifications(prev => [...prev, data.message]);
        setTimeout(() => {
          setNotifications(prev => prev.filter(msg => msg !== data.message));
        }, 4000);
      }
    };
    
    setSocket(ws);

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [BE]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    
    // Mappa i nomi dei campi dal form alle API
    const fieldMapping = {
      ragioneSociale: 'ragione_sociale',
      partitaIva: 'partita_iva',
      codiceFiscale: 'codice_fiscale',
      rappresentanteLegale: 'rappresentante_legale',
      cfRappresentante: 'cf_rappresentante',
      settoreAttivita: 'settore_attivita',
      numeroDipendenti: 'numero_dipendenti'
    };
    
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    const newFiles = files.map(file => ({
      id: Date.now() + Math.random(),
      file,
      name: file.name,
      size: file.size,
      type: file.type
    }));
    
    setUploadedFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (fileId) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const extractDataFromDocuments = async () => {
    if (uploadedFiles.length === 0) {
      alert("Carica almeno un documento per estrarre i dati");
      return;
    }

    setIsExtracting(true);
    setExtractionResults(null);
    
    try {
      const formData = new FormData();
      uploadedFiles.forEach(fileInfo => {
        formData.append('files', fileInfo.file);
      });

      const response = await fetch(`${BE}/admin/clients/extract-data`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        
        if (result.success && result.data) {
          setExtractionResults(result.data);
        } else {
          alert(`Errore nell'estrazione: ${result.error || 'Errore sconosciuto'}`);
        }
      } else {
        const errorData = await response.json();
        alert(`Errore del server: ${errorData.detail || 'Errore sconosciuto'}`);
      }
    } catch (error) {
      console.error("Errore estrazione:", error);
      alert("Errore di connessione durante l'estrazione dati");
    } finally {
      setIsExtracting(false);
    }
  };

  const applyExtractedData = () => {
    if (extractionResults) {
      // Mappa i dati dall'API al form
      const mappedData = {
        ragioneSociale: extractionResults.ragione_sociale || "",
        partitaIva: extractionResults.partita_iva || "",
        codiceFiscale: extractionResults.codice_fiscale || "",
        telefono: extractionResults.telefono || "",
        email: extractionResults.email || "",
        pec: extractionResults.pec || "",
        indirizzo: extractionResults.indirizzo || "",
        citta: extractionResults.citta || "",
        cap: extractionResults.cap || "",
        provincia: extractionResults.provincia || "",
        rappresentanteLegale: extractionResults.rappresentante_legale || "",
        cfRappresentante: extractionResults.cf_rappresentante || "",
        settoreAttivita: extractionResults.settore_attivita || "",
        numeroDipendenti: extractionResults.numero_dipendenti || ""
      };

      setFormData(prev => ({
        ...prev,
        ...mappedData
      }));
      
      setExtractionResults(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Prepara i dati per l'API
      const clientData = {
        ragione_sociale: formData.ragioneSociale,
        partita_iva: formData.partitaIva,
        codice_fiscale: formData.codiceFiscale || null,
        telefono: formData.telefono || null,
        email: formData.email,
        pec: formData.pec || null,
        indirizzo: formData.indirizzo || null,
        citta: formData.citta || null,
        cap: formData.cap || null,
        provincia: formData.provincia || null,
        rappresentante_legale: formData.rappresentanteLegale || null,
        cf_rappresentante: formData.cfRappresentante || null,
        settore_attivita: formData.settoreAttivita || null,
        numero_dipendenti: formData.numeroDipendenti ? parseInt(formData.numeroDipendenti) : null,
        note: formData.note || null
      };

      const response = await fetch(`${BE}/admin/clients/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(clientData)
      });

      if (response.ok) {
        const newClient = await response.json();
        
        // Se ci sono documenti, salvali su OneDrive
        if (uploadedFiles.length > 0) {
          await saveDocumentsToOneDrive(newClient.id);
        }
        
        alert("Cliente creato con successo!");
        onBack();
      } else {
        const errorData = await response.json();
        alert(`Errore nella creazione: ${errorData.detail || 'Errore sconosciuto'}`);
      }
    } catch (error) {
      console.error("Errore creazione cliente:", error);
      alert("Errore di connessione durante la creazione del cliente");
    } finally {
      setIsSubmitting(false);
    }
  };

  const saveDocumentsToOneDrive = async (clientId) => {
    try {
      const formData = new FormData();
      uploadedFiles.forEach(fileInfo => {
        formData.append('files', fileInfo.file);
      });

      await fetch(`${BE}/admin/clients/${clientId}/save-documents`, {
        method: 'POST',
        body: formData
      });
    } catch (error) {
      console.error("Errore salvataggio documenti:", error);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={styles.formContainer}>
      {/* Notifiche */}
      {notifications.map((message, index) => (
        <div key={index} className={styles.notification}>
          <FaCheckCircle className={styles.successIcon} /> {message}
        </div>
      ))}

      <div className={styles.formHeader}>
        <button onClick={onBack} className={styles.backButton}>
          <FaArrowLeft /> Indietro
        </button>
      </div>

      {/* Sezione Upload Documenti */}
      <div className={styles.documentSection}>
        <h3>Carica Documenti</h3>
        <p>Carica documenti aziendali per estrarre automaticamente le informazioni</p>
        
        <div className={styles.uploadArea}>
          <input
            type="file"
            id="fileUpload"
            multiple
            accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.txt"
            onChange={handleFileUpload}
            className={styles.hiddenInput}
          />
          <label htmlFor="fileUpload" className={styles.uploadButton}>
            <FaUpload /> Seleziona Documenti
          </label>
        </div>

        {uploadedFiles.length > 0 && (
          <div className={styles.fileList}>
            <h4>Documenti Caricati:</h4>
            {uploadedFiles.map(file => (
              <div key={file.id} className={styles.fileItem}>
                <FaFileAlt className={styles.fileIcon} />
                <div className={styles.fileInfo}>
                  <span className={styles.fileName}>{file.name}</span>
                  <span className={styles.fileSize}>{formatFileSize(file.size)}</span>
                </div>
                <button
                  onClick={() => removeFile(file.id)}
                  className={styles.removeFile}
                >
                  <FaTimes />
                </button>
              </div>
            ))}
            
            <button
              onClick={extractDataFromDocuments}
              className={styles.extractButton}
              disabled={isExtracting}
            >
              {isExtracting ? (
                <AiOutlineLoading3Quarters className={styles.spinner} />
              ) : (
                <FaRobot />
              )}
              {isExtracting ? "Estrazione in corso..." : "Estrai Dati Automaticamente"}
            </button>
          </div>
        )}

        {extractionResults && (
          <div className={styles.extractionResults}>
            <h4>Dati Estratti:</h4>
            <div className={styles.extractedData}>
              {extractionResults.ragione_sociale && (
                <p><strong>Ragione Sociale:</strong> {extractionResults.ragione_sociale}</p>
              )}
              {extractionResults.partita_iva && (
                <p><strong>P.IVA:</strong> {extractionResults.partita_iva}</p>
              )}
              {extractionResults.rappresentante_legale && (
                <p><strong>Rappresentante Legale:</strong> {extractionResults.rappresentante_legale}</p>
              )}
              {extractionResults.indirizzo && (
                <p><strong>Indirizzo:</strong> {extractionResults.indirizzo}, {extractionResults.citta}</p>
              )}
              {extractionResults.email && (
                <p><strong>Email:</strong> {extractionResults.email}</p>
              )}
            </div>
            <button onClick={applyExtractedData} className={styles.applyButton}>
              Applica Dati Estratti
            </button>
          </div>
        )}
      </div>

      {/* Form Principale - resto del codice uguale */}
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.section}>
          <h3>Informazioni Aziendali</h3>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Ragione Sociale *</label>
              <input
                type="text"
                name="ragioneSociale"
                value={formData.ragioneSociale}
                onChange={handleInputChange}
                required
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Partita IVA *</label>
              <input
                type="text"
                name="partitaIva"
                value={formData.partitaIva}
                onChange={handleInputChange}
                required
                pattern="[0-9]{11}"
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Codice Fiscale</label>
              <input
                type="text"
                name="codiceFiscale"
                value={formData.codiceFiscale}
                onChange={handleInputChange}
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Settore di Attività</label>
              <select
                name="settoreAttivita"
                value={formData.settoreAttivita}
                onChange={handleInputChange}
                className={styles.input}
              >
                <option value="">Seleziona settore</option>
                <option value="manifatturiero">Manifatturiero</option>
                <option value="servizi">Servizi</option>
                <option value="commercio">Commercio</option>
                <option value="costruzioni">Costruzioni</option>
                <option value="trasporti">Trasporti</option>
                <option value="sanitario">Sanitario</option>
                <option value="altro">Altro</option>
              </select>
            </div>

            <div className={styles.formGroup}>
              <label>Numero Dipendenti</label>
              <input
                type="number"
                name="numeroDipendenti"
                value={formData.numeroDipendenti}
                onChange={handleInputChange}
                className={styles.input}
              />
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h3>Contatti</h3>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Telefono</label>
              <input
                type="tel"
                name="telefono"
                value={formData.telefono}
                onChange={handleInputChange}
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Email *</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>PEC</label>
              <input
                type="email"
                name="pec"
                value={formData.pec}
                onChange={handleInputChange}
                className={styles.input}
              />
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h3>Indirizzo</h3>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Indirizzo *</label>
              <input
                type="text"
                name="indirizzo"
                value={formData.indirizzo}
                onChange={handleInputChange}
                required
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Città *</label>
              <input
                type="text"
                name="citta"
                value={formData.citta}
                onChange={handleInputChange}
                required
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>CAP</label>
              <input
                type="text"
                name="cap"
                value={formData.cap}
                onChange={handleInputChange}
                pattern="[0-9]{5}"
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Provincia</label>
              <input
                type="text"
                name="provincia"
                value={formData.provincia}
                onChange={handleInputChange}
                maxLength="2"
                className={styles.input}
              />
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h3>Rappresentante Legale</h3>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Nome e Cognome *</label>
              <input
                type="text"
                name="rappresentanteLegale"
                value={formData.rappresentanteLegale}
                onChange={handleInputChange}
                required
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Codice Fiscale Rappresentante</label>
              <input
                type="text"
                name="cfRappresentante"
                value={formData.cfRappresentante}
                onChange={handleInputChange}
                pattern="[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]"
                className={styles.input}
              />
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h3>Note Aggiuntive</h3>
          <div className={styles.formGroup}>
            <textarea
              name="note"
              value={formData.note}
              onChange={handleInputChange}
              rows="4"
              className={styles.textarea}
              placeholder="Eventuali note o informazioni aggiuntive..."
            />
          </div>
        </div>

        <div className={styles.formActions}>
          <button
            type="button"
            onClick={onBack}
            className={styles.cancelButton}
          >
            Annulla
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className={styles.submitButton}
          >
            {isSubmitting ? (
              <>
                <AiOutlineLoading3Quarters className={styles.spinner} />
                Creazione in corso...
              </>
            ) : (
              "Crea Cliente"
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AdminClientForm;