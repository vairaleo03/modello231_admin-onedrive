import React, { useState, useEffect } from "react";
import { FaArrowLeft, FaSearch, FaCalendarAlt, FaUser, FaBuilding } from "react-icons/fa";
import styles from "../styles/admin-forms.module.css";

const AdminOdvForm = ({ onBack }) => {
  const [formData, setFormData] = useState({
    nome: "",
    cognome: "",
    codiceFiscale: "",
    email: "",
    telefono: "",
    professione: "",
    abilitazione: "",
    numeroAlbo: "",
    dataInizioCarica: new Date().toISOString().split('T')[0],
    dataFineCarica: "",
    clienteAssegnato: "",
    note: ""
  });

  const [clientiList, setClientiList] = useState([]);
  const [filteredClienti, setFilteredClienti] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [showClientList, setShowClientList] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Mock data per la lista clienti
  useEffect(() => {
    const mockClienti = [
      { id: 1, ragioneSociale: "AZIENDA ALPHA S.R.L.", citta: "Bari", settore: "Manifatturiero" },
      { id: 2, ragioneSociale: "BETA COSTRUZIONI S.P.A.", citta: "Lecce", settore: "Costruzioni" },
      { id: 3, ragioneSociale: "GAMMA SERVIZI S.R.L.", citta: "Taranto", settore: "Servizi" },
      { id: 4, ragioneSociale: "DELTA COMMERCIO S.A.S.", citta: "Foggia", settore: "Commercio" },
      { id: 5, ragioneSociale: "EPSILON TRASPORTI S.R.L.", citta: "Brindisi", settore: "Trasporti" },
      { id: 6, ragioneSociale: "ZETA HEALTHCARE S.P.A.", citta: "Bari", settore: "Sanitario" }
    ];
    setClientiList(mockClienti);
    setFilteredClienti(mockClienti);
  }, []);

  // Calcola automaticamente la data di fine carica (3 anni dopo l'inizio)
  useEffect(() => {
    if (formData.dataInizioCarica) {
      const dataInizio = new Date(formData.dataInizioCarica);
      const dataFine = new Date(dataInizio);
      dataFine.setFullYear(dataFine.getFullYear() + 3);
      
      setFormData(prev => ({
        ...prev,
        dataFineCarica: dataFine.toISOString().split('T')[0]
      }));
    }
  }, [formData.dataInizioCarica]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSearchCliente = (searchValue) => {
    setSearchTerm(searchValue);
    if (searchValue === "") {
      setFilteredClienti(clientiList);
    } else {
      const filtered = clientiList.filter(cliente =>
        cliente.ragioneSociale.toLowerCase().includes(searchValue.toLowerCase()) ||
        cliente.citta.toLowerCase().includes(searchValue.toLowerCase()) ||
        cliente.settore.toLowerCase().includes(searchValue.toLowerCase())
      );
      setFilteredClienti(filtered);
    }
  };

  const selectCliente = (cliente) => {
    setFormData(prev => ({
      ...prev,
      clienteAssegnato: cliente.id
    }));
    setSearchTerm(cliente.ragioneSociale);
    setShowClientList(false);
  };

  const getSelectedClienteInfo = () => {
    return clientiList.find(c => c.id === parseInt(formData.clienteAssegnato));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulazione salvataggio (mock API call)
    setTimeout(() => {
      alert("Addetto OdV creato con successo!");
      setIsSubmitting(false);
      onBack();
    }, 2000);
  };

  const selectedCliente = getSelectedClienteInfo();

  return (
    <div className={styles.formContainer}>
      <div className={styles.formHeader}>
        <button onClick={onBack} className={styles.backButton}>
          <FaArrowLeft /> Indietro
        </button>
      </div>

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.section}>
          <h3>Informazioni Personali</h3>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Nome *</label>
              <input
                type="text"
                name="nome"
                value={formData.nome}
                onChange={handleInputChange}
                required
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Cognome *</label>
              <input
                type="text"
                name="cognome"
                value={formData.cognome}
                onChange={handleInputChange}
                required
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Codice Fiscale *</label>
              <input
                type="text"
                name="codiceFiscale"
                value={formData.codiceFiscale}
                onChange={handleInputChange}
                required
                pattern="[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]"
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
              <label>Telefono</label>
              <input
                type="tel"
                name="telefono"
                value={formData.telefono}
                onChange={handleInputChange}
                className={styles.input}
              />
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h3>Qualifiche Professionali</h3>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Professione *</label>
              <select
                name="professione"
                value={formData.professione}
                onChange={handleInputChange}
                required
                className={styles.input}
              >
                <option value="">Seleziona professione</option>
                <option value="avvocato">Avvocato</option>
                <option value="commercialista">Commercialista</option>
                <option value="consulente_lavoro">Consulente del Lavoro</option>
                <option value="ingegnere">Ingegnere</option>
                <option value="esperto_231">Esperto D.Lgs. 231/01</option>
                <option value="altro">Altro</option>
              </select>
            </div>

            <div className={styles.formGroup}>
              <label>Abilitazione/Albo</label>
              <input
                type="text"
                name="abilitazione"
                value={formData.abilitazione}
                onChange={handleInputChange}
                placeholder="es. Ordine degli Avvocati"
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Numero Albo</label>
              <input
                type="text"
                name="numeroAlbo"
                value={formData.numeroAlbo}
                onChange={handleInputChange}
                className={styles.input}
              />
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h3>Carica OdV</h3>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Data Inizio Carica *</label>
              <input
                type="date"
                name="dataInizioCarica"
                value={formData.dataInizioCarica}
                onChange={handleInputChange}
                required
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Data Fine Carica Stimata</label>
              <input
                type="date"
                name="dataFineCarica"
                value={formData.dataFineCarica}
                onChange={handleInputChange}
                className={styles.input}
              />
              <small className={styles.helpText}>
                <FaCalendarAlt /> Calcolata automaticamente (3 anni)
              </small>
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h3>Assegnazione Cliente</h3>
          
          <div className={styles.clientSearchContainer}>
            <div className={styles.searchInputGroup}>
              <FaSearch className={styles.searchIcon} />
              <input
                type="text"
                placeholder="Cerca cliente per ragione sociale, città o settore..."
                value={searchTerm}
                onChange={(e) => handleSearchCliente(e.target.value)}
                onFocus={() => setShowClientList(true)}
                className={styles.searchInput}
              />
            </div>

            {showClientList && (
              <div className={styles.clientDropdown}>
                {filteredClienti.length > 0 ? (
                  filteredClienti.map(cliente => (
                    <div
                      key={cliente.id}
                      className={styles.clientOption}
                      onClick={() => selectCliente(cliente)}
                    >
                      <div className={styles.clientInfo}>
                        <FaBuilding className={styles.clientIcon} />
                        <div>
                          <div className={styles.clientName}>{cliente.ragioneSociale}</div>
                          <div className={styles.clientDetails}>
                            {cliente.citta} • {cliente.settore}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className={styles.noClients}>Nessun cliente trovato</div>
                )}
              </div>
            )}
          </div>

          {selectedCliente && (
            <div className={styles.selectedClient}>
              <h4>Cliente Selezionato:</h4>
              <div className={styles.clientCard}>
                <FaBuilding className={styles.clientCardIcon} />
                <div>
                  <div className={styles.clientCardName}>{selectedCliente.ragioneSociale}</div>
                  <div className={styles.clientCardDetails}>
                    {selectedCliente.citta} • {selectedCliente.settore}
                  </div>
                </div>
              </div>
            </div>
          )}
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
              placeholder="Eventuali note sull'addetto OdV..."
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
            disabled={isSubmitting || !formData.clienteAssegnato}
            className={styles.submitButton}
          >
            {isSubmitting ? "Creazione in corso..." : "Crea Addetto OdV"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AdminOdvForm;