import { useRef, useEffect, useState } from "react";
import Link from "next/link";
import styles from "../styles/header.module.css";
import { FaUserCircle, FaCog, FaUserShield } from "react-icons/fa";
import {
  SignedIn,
  SignedOut,
  SignInButton,
  SignUpButton,
  UserButton,
  useUser,
} from "@clerk/nextjs";

const Header = () => {
  const { user } = useUser();
  const isAdmin = user?.publicMetadata?.role === "admin";

  const [showSettings, setShowSettings] = useState(false);
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [promptContent, setPromptContent] = useState("");
  const [loadingPrompt, setLoadingPrompt] = useState(false);
  const modalRef = useRef(null);
  const gearButtonRef = useRef(null);
  const BE = process.env.NEXT_PUBLIC_BE;

  const fetchPrompt = async () => {
    setLoadingPrompt(true);
    const res = await fetch(`${BE}/api/prompts/1`);
    const data = await res.json();
    setPromptContent(data.content || "");
    setLoadingPrompt(false);
  };

  const savePrompt = async () => {
    await fetch(`${BE}/api/prompts/1`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: promptContent }),
    });
    setShowPromptModal(false);
  };

  useEffect(() => {
    function handleClickOutside(event) {
      if (
        modalRef.current &&
        !modalRef.current.contains(event.target) &&
        gearButtonRef.current &&
        !gearButtonRef.current.contains(event.target)
      ) {
        setShowSettings(false);
      }
    }
  
    if (showSettings) {
      document.addEventListener("mousedown", handleClickOutside);
    }
  
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showSettings]);

  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        <Link href="/dashboard">
          <span>in-compliance</span>
          <img src="/logo_header.png" alt="Logo" />
        </Link>
      </div>

      <SignedIn>
        <nav className={styles.nav}>
          {isAdmin && (
            <Link href="/admin-dashboard" className={styles.adminLink}>
              <FaUserShield className={styles.adminIcon} />
              Admin Dashboard
            </Link>
          )}
          {/* Altri link di navigazione se necessari */}
        </nav>
      </SignedIn>

      <div className={styles.userIcon}>
        
        <SignedOut>
          <SignInButton mode="modal" redirectUrl="/dashboard">
            <button className={styles.loginBtn}>Accedi</button>
          </SignInButton>
          <SignUpButton mode="modal" redirectUrl="/dashboard">
            <button className={styles.registerBtn}>Registrati</button>
          </SignUpButton>
        </SignedOut>

        <SignedIn>
          {isAdmin && (
            <>
              <button
                ref={gearButtonRef}
                onClick={(e) => {
                  e.stopPropagation(); // Impedisce al click di arrivare al listener globale
                  setShowSettings((prev) => !prev);
                }}
                className={styles.gearButton}
              >
                <FaCog />
              </button>
              {showSettings && (
                <div ref={modalRef} className={`${styles.settingsModal} ${showSettings ? styles.show : ""}`}>
                  <button
                    onClick={() => {
                      fetchPrompt();
                      setShowPromptModal(true);
                      setShowSettings(false);
                    }}
                    className={styles.settingsModalBtn}
                  >
                    Modifica prompt verbali
                  </button>
                </div>
              )}
            </>
          )}

          <UserButton afterSignOutUrl="/" />
          
        </SignedIn>
      </div>

      {/* Prompt Modal */}
      {showPromptModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContainer}>
            <h2 className={styles.modalTitle}>Modifica Prompt Verbali</h2>
            {loadingPrompt ? (
              <p>Caricamento...</p>
            ) : (
              <textarea
                value={promptContent}
                onChange={(e) => setPromptContent(e.target.value)}
                className={styles.textarea}
              />
            )}
            <div className={styles.modalActions}>
              <button onClick={() => setShowPromptModal(false)} className={styles.cancelBtn}>Annulla</button>
              <button onClick={savePrompt} className={styles.saveBtn}>Salva</button>
            </div>
          </div>
        </div>
      )}

    </header>
  );
};

export default Header;