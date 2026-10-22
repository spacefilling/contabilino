"""
Contabilino - Entry point
Programma di contabilità in partita doppia per piccole attività.
All'avvio chiede di creare o aprire un database SQLite.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import tema
from db import Database
from ui import MainWindow


def get_base_dir():
    """Restituisce la directory dell'eseguibile o dello script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def startup_dialog():
    """Mostra il dialogo iniziale per creare o aprire un database."""
    root = tk.Tk()
    root.withdraw()
    tema.imposta_icona(root)  # anche le finestre di avvio hanno il logo

    base_dir = get_base_dir()
    default_db = os.path.join(base_dir, "contabilino.db")

    # Se esiste un database nella stessa cartella, lo apre direttamente
    if os.path.exists(default_db):
        root.destroy()
        return default_db, False

    # Altrimenti chiede cosa fare
    result = messagebox.askyesnocancel(
        "Contabilino",
        "Nessun database trovato nella cartella corrente.\n\n"
        "Vuoi creare un nuovo database?\n\n"
        "Sì = Crea nuovo database\n"
        "No = Apri database esistente\n"
        "Annulla = Esci",
    )

    if result is None:
        root.destroy()
        sys.exit(0)
    elif result:
        filepath = filedialog.asksaveasfilename(
            title="Crea nuovo database",
            initialdir=base_dir,
            initialfile="contabilino.db",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("Tutti i file", "*.*")],
        )
        if not filepath:
            root.destroy()
            sys.exit(0)
        root.destroy()
        return filepath, True
    else:
        filepath = filedialog.askopenfilename(
            title="Apri database esistente",
            initialdir=base_dir,
            filetypes=[("SQLite Database", "*.db"), ("Tutti i file", "*.*")],
        )
        if not filepath:
            root.destroy()
            sys.exit(0)
        root.destroy()
        return filepath, False


def main():
    tema.abilita_dpi()  # prima di qualsiasi finestra: testo nitido con lo zoom di Windows
    db_path, is_new = startup_dialog()

    db = Database(db_path)
    db.connect()

    if is_new:
        db.init_db()
    else:
        db.create_tables()

    root = tk.Tk()
    tema.applica(root)
    app = MainWindow(root, db)

    # Se l'apertura ha aggiornato la struttura del database, avvisa dov'è la copia
    if db.backup_path:
        messagebox.showinfo(
            "Database aggiornato",
            "Il database è stato aggiornato al nuovo formato degli esercizi\n"
            "(periodo con data di inizio e data di fine).\n\n"
            "Gli esercizi esistenti sono diventati periodi 01/01 - 31/12.\n"
            f"Copia di sicurezza del database precedente:\n{db.backup_path}",
        )

    def on_closing():
        db.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
