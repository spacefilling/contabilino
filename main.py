"""
Contabilino - Entry point
Programma di contabilità in partita doppia per piccole attività.
All'avvio apre l'archivio della cartella del programma, oppure chiede quale
archivio aprire o se crearne uno nuovo (vedi avvio.py).
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

import tema
from avvio import scegli_archivio
from db import Database
from ui import MainWindow


def get_base_dir():
    """
    Cartella del programma, dove stanno anche gli archivi: quella dell'eseguibile
    (o dello script). Su Mac l'eseguibile è dentro Contabilino.app/Contents/MacOS:
    la cartella giusta è quella che contiene Contabilino.app.
    """
    if getattr(sys, "frozen", False):
        cartella = os.path.dirname(sys.executable)
        if sys.platform == "darwin" and cartella.endswith(os.path.join(".app", "Contents", "MacOS")):
            cartella = os.path.dirname(os.path.dirname(os.path.dirname(cartella)))
        return cartella
    return os.path.dirname(os.path.abspath(__file__))


def cartella_utilizzabile(cartella):
    """
    Controlla che nella cartella del programma si possa scrivere l'archivio.
    Su Mac un'app appena scaricata viene avviata da una posizione temporanea
    di sola lettura (App Translocation): va prima spostata.
    """
    if "/AppTranslocation/" in cartella:
        return ("macOS ha avviato Contabilino da una posizione temporanea, dove non può "
                "salvare i dati.\n\nSposta Contabilino.app in un'altra cartella (per esempio "
                "nella cartella dove vuoi tenere i dati, o su una chiavetta) trascinandola con "
                "il Finder, poi riaprila.")
    if not os.access(cartella, os.W_OK):
        return (f"Nella cartella del programma non si può scrivere:\n{cartella}\n\n"
                "Sposta Contabilino in una cartella dove hai i permessi di scrittura "
                "(per esempio Documenti, il Desktop o una chiavetta USB) e riaprilo.")
    return None


def main():
    tema.abilita_dpi()  # prima di qualsiasi finestra: testo nitido con lo zoom di Windows
    cartella = get_base_dir()

    problema = cartella_utilizzabile(cartella)
    if problema:
        root = tk.Tk()
        root.withdraw()
        tema.imposta_icona(root)
        messagebox.showerror("Contabilino", problema)
        root.destroy()
        sys.exit(1)

    scelta = scegli_archivio(cartella)
    if not scelta:
        sys.exit(0)
    db_path, is_new = scelta

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
