import React, { useState, useEffect } from "react";
import { FaArrowLeft, FaEdit, FaTrash, FaEye, FaPlus, FaSearch } from "react-icons/fa";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import styles from "../styles/client-management.module.css";

const ClientManagement = ({ onBack, onCreateNew }) => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedClient, setSelectedClient] = useState(null);
  const [view, setView] = useState("list"); // "list", "view", "edit"
  const [searchTerm, setSearchTerm] = useState("");
  const [notifications, setNotifications] = useState([]);

  const BE = process.env.NEXT_PUBLIC_BE;

  // Carica lista clienti
  useEffect(() => {
    fetchClients();
  }, []);

  const fetchClients = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BE}/admin/clients/`);
      if (response.ok) {
        const data = await response.json();
        setClients(data);
      } else {
        console.error("Errore nel caricamento clienti");
      }
    } catch (error) {
      console.error("Errore:", error);
    } finally {
      setLoading(false);
    }
  };

  // Carica dettagli cliente
  const fetchClientDetails = async (clientId) => {
    try {
      const response = await fetch(`${BE}/admin/clients/${clientId}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedClient(data);
      }
    } catch (error) {
      console.error("Errore:", error);
    }
  };

  // Elimina cliente
  const deleteClient = async (clientId) => {
    if (!confirm("Sei sicuro di voler eliminare questo cliente?")) return;

    try {
      const response = await fetch(`${BE}/admin/clients/${clientId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setNotifications(prev => [...prev, "Cliente eliminato con successo"]);
        fetchClients(); // Ricarica lista
        setView("list");
        setTimeout(() => {
          setNotifications(prev => prev.filter((_, i) => i !== 0));
        }, 3000);
      } else {
        alert("Errore nell'eliminazione del cliente");
      }
    } catch (error) {
      console.error("Errore:", error);
      alert("Errore di connessione");
    }
  };

  // Filtra clienti per ricerca
  const filteredClients = clients.filter(client =>
    client.ragione_sociale.toLowerCase().includes(searchTerm.toLowerCase()) ||
    client.partita_iva.includes(searchTerm) ||
    (client.citta && client.citta.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Lista clienti
  const renderClientList = () => (
    <div className={styles.clientsContainer}>
      {/* Header con ricerca */}
      <div className={styles.clientsHeader}>
        <h2>Gestione Clienti ({clients.length})</h2>
        <div className={styles.clientsActions}>
          <div className={styles.searchContainer}>
            <FaSearch className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Cerca per ragione sociale, P.IVA o città..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={styles.searchInput}
            />
          </div>
          <button onClick={onCreateNew} className={styles.createButton}>
            <FaPlus /> Nuovo Cliente
          </button>
        </div>
      </div>

      {/* Tabella clienti */}
      {loading ? (
        <div className={styles.loading}>
          <AiOutlineLoading3Quarters className={styles.spinner} />
          Caricamento clienti...
        </div>
      ) : filteredClients.length === 0 ? (
        <div className={styles.emptyState}>
          <p>Nessun cliente trovato</p>
          <button onClick={onCreateNew} className={styles.createButton}>
            <FaPlus /> Crea il primo cliente
          </button>
        </div>
      ) : (
        <div className={styles.clientsTable}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Ragione Sociale</th>
                <th>Partita IVA</th>
                <th>Città</th>
                <th>Settore</th>
                <th>Creato</th>
                <th>Azioni</th>
              </tr>
            </thead>
            <tbody>
              {filteredClients.map(client => (
                <tr key={client.id}>
                  <td className={styles.clientName}>
                    <strong>{client.ragione_sociale}</strong>
                  </td>
                  <td>{client.partita_iva}</td>
                  <td>{client.citta || "-"}</td>
                  <td>{client.settore_attivita || "-"}</td>
                  <td>{new Date(client.created_at).toLocaleDateString()}</td>
                  <td className={styles.actions}>
                    <button 
                      onClick={() => viewClient(client.id)}
                      className={styles.actionButton}
                      title="Visualizza"
                    >
                      <FaEye />
                    </button>
                    <button 
                      onClick={() => editClient(client.id)}
                      className={styles.actionButton}
                      title="Modifica"
                    >
                      <FaEdit />
                    </button>
                    <button 
                      onClick={() => deleteClient(client.id)}
                      className={`${styles.actionButton} ${styles.deleteButton}`}
                      title="Elimina"
                    >
                      <FaTrash />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  // Visualizza dettagli cliente
  const viewClient = async (clientId) => {
    await fetchClientDetails(clientId);
    setView("view");
  };

  // Modifica cliente
  const editClient = async (clientId) => {
    await fetchClientDetails(clientId);
    setView("edit");
  };

  // Renderizza dettagli cliente
  const renderClientDetails = () => (
    <div className={styles.clientDetails}>
      <div className={styles.detailsHeader}>
        <button onClick={() => setView("list")} className={styles.backButton}>
          <FaArrowLeft /> Torna alla lista
        </button>
        <div className={styles.detailsActions}>
          {view === "view" && (
            <button 
              onClick={() => setView("edit")} 
              className={styles.editButton}
            >
              <FaEdit /> Modifica
            </button>
          )}
          <button 
            onClick={() => deleteClient(selectedClient.id)}
            className={styles.deleteButton}
          >
            <FaTrash /> Elimina
          </button>
        </div>
      </div>

      <div className={styles.detailsContent}>
        <h2>{selectedClient.ragione_sociale}</h2>
        
        <div className={styles.detailsGrid}>
          <div className={styles.detailsSection}>
            <h3>Informazioni Aziendali</h3>
            <div className={styles.detailsRow}>
              <span>Partita IVA:</span>
              <span>{selectedClient.partita_iva}</span>
            </div>
            <div className={styles.detailsRow}>
              <span>Codice Fiscale:</span>
              <span>{selectedClient.codice_fiscale || "-"}</span>
            </div>
            <div className={styles.detailsRow}>
              <span>Settore:</span>
              <span>{selectedClient.settore_attivita || "-"}</span>
            </div>
            <div className={styles.detailsRow}>
              <span>Dipendenti:</span>
              <span>{selectedClient.numero_dipendenti || "-"}</span>
            </div>
          </div>

          <div className={styles.detailsSection}>
            <h3>Contatti</h3>
            <div className={styles.detailsRow}>
              <span>Email:</span>
              <span>{selectedClient.email}</span>
            </div>
            <div className={styles.detailsRow}>
              <span>PEC:</span>
              <span>{selectedClient.pec || "-"}</span>
            </div>
            <div className={styles.detailsRow}>
              <span>Telefono:</span>
              <span>{selectedClient.telefono || "-"}</span>
            </div>
          </div>

          <div className={styles.detailsSection}>
            <h3>Indirizzo</h3>
            <div className={styles.detailsRow}>
              <span>Indirizzo:</span>
              <span>{selectedClient.indirizzo || "-"}</span>
            </div>
            <div className={styles.detailsRow}>
              <span>Città:</span>
              <span>{selectedClient.citta || "-"} {selectedClient.cap || ""}</span>
            </div>
            <div className={styles.detailsRow}>
              <span>Provincia:</span>
              <span>{selectedClient.provincia || "-"}</span>
            </div>
          </div>

          <div className={styles.detailsSection}>
            <h3>Rappresentante Legale</h3>
            <div className={styles.detailsRow}>
              <span>Nome:</span>
              <span>{selectedClient.rappresentante_legale || "-"}</span>
            </div>
            <div className={styles.detailsRow}>
              <span>Codice Fiscale:</span>
              <span>{selectedClient.cf_rappresentante || "-"}</span>
            </div>
          </div>
        </div>

        {selectedClient.note && (
          <div className={styles.detailsSection}>
            <h3>Note</h3>
            <p>{selectedClient.note}</p>
          </div>
        )}

        <div className={styles.detailsSection}>
          <h3>Informazioni Sistema</h3>
          <div className={styles.detailsRow}>
            <span>Creato:</span>
            <span>{new Date(selectedClient.created_at).toLocaleString()}</span>
          </div>
          <div className={styles.detailsRow}>
            <span>Aggiornato:</span>
            <span>{new Date(selectedClient.updated_at).toLocaleString()}</span>
          </div>
          {selectedClient.documents_path && (
            <div className={styles.detailsRow}>
              <span>Documenti OneDrive:</span>
              <span>{selectedClient.documents_path}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // Form modifica cliente
  const renderEditForm = () => {
    const [formData, setFormData] = useState(selectedClient);
    const [saving, setSaving] = useState(false);

    const handleInputChange = (e) => {
      const { name, value } = e.target;
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    };

    const handleSubmit = async (e) => {
      e.preventDefault();
      setSaving(true);

      try {
        const response = await fetch(`${BE}/admin/clients/${selectedClient.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            ragione_sociale: formData.ragione_sociale,
            partita_iva: formData.partita_iva,
            codice_fiscale: formData.codice_fiscale || null,
            telefono: formData.telefono || null,
            email: formData.email,
            pec: formData.pec || null,
            indirizzo: formData.indirizzo || null,
            citta: formData.citta || null,
            cap: formData.cap || null,
            provincia: formData.provincia || null,
            rappresentante_legale: formData.rappresentante_legale || null,
            cf_rappresentante: formData.cf_rappresentante || null,
            settore_attivita: formData.settore_attivita || null,
            numero_dipendenti: formData.numero_dipendenti ? parseInt(formData.numero_dipendenti) : null,
            note: formData.note || null
          })
        });

        if (response.ok) {
          setNotifications(prev => [...prev, "Cliente aggiornato con successo"]);
          setSelectedClient(formData);
          setView("view");
          fetchClients(); // Ricarica lista
          setTimeout(() => {
            setNotifications(prev => prev.filter((_, i) => i !== 0));
          }, 3000);
        } else {
          const errorData = await response.json();
          alert(`Errore: ${errorData.detail || 'Errore sconosciuto'}`);
        }
      } catch (error) {
        console.error("Errore:", error);
        alert("Errore di connessione");
      } finally {
        setSaving(false);
      }
    };

    return (
      <div className={styles.editForm}>
        <div className={styles.formHeader}>
          <button onClick={() => setView("view")} className={styles.backButton}>
            <FaArrowLeft /> Annulla
          </button>
          <h2>Modifica Cliente</h2>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.section}>
            <h3>Informazioni Aziendali</h3>
            <div className={styles.formGrid}>
              <div className={styles.formGroup}>
                <label>Ragione Sociale *</label>
                <input
                  type="text"
                  name="ragione_sociale"
                  value={formData.ragione_sociale || ""}
                  onChange={handleInputChange}
                  required
                  className={styles.input}
                />
              </div>
              <div className={styles.formGroup}>
                <label>Partita IVA *</label>
                <input
                  type="text"
                  name="partita_iva"
                  value={formData.partita_iva || ""}
                  onChange={handleInputChange}
                  required
                  className={styles.input}
                />
              </div>
              <div className={styles.formGroup}>
                <label>Settore</label>
                <select
                  name="settore_attivita"
                  value={formData.settore_attivita || ""}
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
            </div>
          </div>

          <div className={styles.section}>
            <h3>Contatti</h3>
            <div className={styles.formGrid}>
              <div className={styles.formGroup}>
                <label>Email *</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email || ""}
                  onChange={handleInputChange}
                  required
                  className={styles.input}
                />
              </div>
              <div className={styles.formGroup}>
                <label>Telefono</label>
                <input
                  type="tel"
                  name="telefono"
                  value={formData.telefono || ""}
                  onChange={handleInputChange}
                  className={styles.input}
                />
              </div>
              <div className={styles.formGroup}>
                <label>PEC</label>
                <input
                  type="email"
                  name="pec"
                  value={formData.pec || ""}
                  onChange={handleInputChange}
                  className={styles.input}
                />
              </div>
            </div>
          </div>

          <div className={styles.formActions}>
            <button type="button" onClick={() => setView("view")} className={styles.cancelButton}>
              Annulla
            </button>
            <button type="submit" disabled={saving} className={styles.submitButton}>
              {saving ? (
                <>
                  <AiOutlineLoading3Quarters className={styles.spinner} />
                  Salvando...
                </>
              ) : (
                "Salva Modifiche"
              )}
            </button>
          </div>
        </form>
      </div>
    );
  };

  return (
    <div className={styles.formContainer}>
      {/* Notifiche */}
      {notifications.map((message, index) => (
        <div key={index} className={styles.notification}>
          ✅ {message}
        </div>
      ))}

      <div className={styles.formHeader}>
        <button onClick={onBack} className={styles.backButton}>
          <FaArrowLeft /> Dashboard
        </button>
      </div>

      {view === "list" && renderClientList()}
      {view === "view" && selectedClient && renderClientDetails()}
      {view === "edit" && selectedClient && renderEditForm()}
    </div>
  );
};

export default ClientManagement;