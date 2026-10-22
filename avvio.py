"""
Contabilino - Avvio: scelta dell'archivio
Finestra di benvenuto che propone gli archivi trovati nella cartella del
programma, oppure di crearne uno nuovo o di aprirne uno da un'altra cartella.
Riconosce gli archivi di Contabilino (anche delle versioni precedenti) senza
modificarli: li apre in sola lettura solo per leggerne il riepilogo.
"""

import glob
import os
import sqlite3
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import tema
from tema import px
from version import VERSIONE

TABELLE = {"esercizi", "conti", "registrazioni", "movimenti"}
NOME_PREDEFINITO = "contabilino.db"


def info_archivio(percorso):
    """
    Riepilogo di un archivio di Contabilino: dict con registrazioni, esercizi
    e data di modifica. None se il file non è un archivio di Contabilino.
    """
    try:
        conn = sqlite3.connect(f"file:{percorso}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        tabelle = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not TABELLE <= tabelle:
            return None
        registrazioni = conn.execute("SELECT COUNT(*) FROM registrazioni").fetchone()[0]
        conn.row_factory = sqlite3.Row
        esercizi = [
            (r["descrizione"] if "descrizione" in r.keys() and r["descrizione"]
             else f"Esercizio {r['anno']}" if "anno" in r.keys() else "Esercizio")
            for r in conn.execute("SELECT * FROM esercizi ORDER BY id DESC")
        ]
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return {
        "percorso": percorso,
        "nome": os.path.basename(percorso),
        "registrazioni": registrazioni,
        "esercizi": esercizi,
        "modificato": datetime.fromtimestamp(os.path.getmtime(percorso)),
    }


def archivi_nella_cartella(cartella):
    """Archivi di Contabilino nella cartella, dal più recente (escluse le copie di sicurezza)."""
    trovati = []
    for percorso in glob.glob(os.path.join(cartella, "*.db")):
        if "_backup_" in os.path.basename(percorso):
            continue
        info = info_archivio(percorso)
        if info:
            trovati.append(info)
    return sorted(trovati, key=lambda i: i["modificato"], reverse=True)


def descrivi(info):
    """Riga di riepilogo: "12 registrazioni · Esercizio 2026 · modificato il 22/10/2026"."""
    n = info["registrazioni"]
    parti = ["nessuna registrazione" if not n else "1 registrazione" if n == 1 else f"{n} registrazioni"]
    if info["esercizi"]:
        parti.append(info["esercizi"][0] + (f" (+{len(info['esercizi']) - 1})" if len(info["esercizi"]) > 1 else ""))
    parti.append(f"modificato il {info['modificato']:%d/%m/%Y}")
    return "  ·  ".join(parti)


class FinestraAvvio:
    """
    Benvenuto e scelta dell'archivio. Dopo mainloop(): risultato = (percorso, piano)
    dove piano è None per un archivio esistente, "semplice" o "completo" per uno
    nuovo; None se l'utente esce.
    """

    def __init__(self, cartella, archivi):
        self.cartella = cartella
        self.archivi = archivi
        self.risultato = None

        self.root = tk.Tk()
        tema.applica(self.root)
        self.root.title("Contabilino")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self._build()

        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 3
        self.root.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _build(self):
        frame = ttk.Frame(self.root, padding=(px(24), px(20), px(24), px(18)))
        frame.pack(fill=tk.BOTH, expand=True)

        # Intestazione
        testata = ttk.Frame(frame)
        testata.pack(fill=tk.X)
        self._logo = tema.logo(self.root, 48)
        ttk.Label(testata, image=self._logo).pack(side=tk.LEFT)
        titoli = ttk.Frame(testata)
        titoli.pack(side=tk.LEFT, padx=(px(12), 0))
        ttk.Label(titoli, text="Benvenuto in Contabilino", style="Titolo.TLabel").pack(anchor=tk.W)
        ttk.Label(titoli, text=f"Contabilità in partita doppia  ·  versione {VERSIONE}",
                  style="Secondario.TLabel").pack(anchor=tk.W)

        # Come funziona: niente installazione, dati in un solo file
        programma = {"win32": "in questo file .exe", "darwin": "in questa app"}.get(sys.platform, "in questo file")
        ttk.Label(
            frame, wraplength=px(520), justify=tk.LEFT, style="Nota.TLabel",
            text=f"Contabilino non si installa: è tutto {programma}. I dati stanno in un "
                 "unico archivio, un file .db: tienilo nella stessa cartella del programma, anche "
                 "su una chiavetta USB. Per fare il backup o portare tutto su un altro computer "
                 "basta copiare la cartella.",
        ).pack(anchor=tk.W, pady=(px(14), px(4)))

        if self.archivi:
            self._build_archivi(frame)
            ttk.Label(frame, text="Oppure", style="Sottotitolo.TLabel").pack(anchor=tk.W, pady=(px(16), px(6)))
        else:
            ttk.Label(
                frame, wraplength=px(520), justify=tk.LEFT,
                text="In questa cartella non c'è ancora un archivio di Contabilino. Se è la prima "
                     "volta che usi il programma, crea un nuovo archivio.",
            ).pack(anchor=tk.W, pady=(px(10), px(10)))

        pulsanti = ttk.Frame(frame)
        pulsanti.pack(fill=tk.X)
        nuovo = ttk.Button(pulsanti, text="Crea un nuovo archivio", command=self._crea,
                           style="TButton" if self.archivi else "Accent.TButton")
        nuovo.pack(fill=tk.X)
        ttk.Button(pulsanti, text="Apri un archivio da un'altra cartella...", command=self._apri_altro).pack(
            fill=tk.X, pady=(px(6), 0))
        ttk.Button(pulsanti, text="Esci", command=self.root.destroy).pack(fill=tk.X, pady=(px(6), 0))
        if not self.archivi:
            nuovo.focus_set()
            self.root.bind("<Return>", lambda e: self._crea())

        ttk.Label(frame, text=f"Cartella del programma: {self.cartella}", style="Secondario.TLabel",
                  wraplength=px(520), justify=tk.LEFT).pack(anchor=tk.W, pady=(px(14), 0))

    def _build_archivi(self, frame):
        n = len(self.archivi)
        ttk.Label(
            frame, style="Sottotitolo.TLabel",
            text="Trovato un archivio in questa cartella" if n == 1 else f"Trovati {n} archivi in questa cartella",
        ).pack(anchor=tk.W, pady=(px(12), px(6)))

        self.lista = ttk.Treeview(frame, columns=("dettagli",), show="tree", height=min(n, 5), selectmode="browse")
        self.lista.column("#0", width=px(170), stretch=False)
        self.lista.column("dettagli", width=px(350))
        for i, info in enumerate(self.archivi):
            self.lista.insert("", tk.END, iid=str(i), text=info["nome"], values=(descrivi(info),))
        self.lista.pack(fill=tk.X)
        self.lista.selection_set("0")
        self.lista.focus("0")
        self.lista.bind("<Double-Button-1>", lambda e: self._apri_selezionato())
        self.lista.bind("<Return>", lambda e: self._apri_selezionato())

        apri = ttk.Button(frame, text="Apri l'archivio selezionato", style="Accent.TButton",
                          command=self._apri_selezionato)
        apri.pack(fill=tk.X, pady=(px(8), 0))
        apri.focus_set()
        self.root.bind("<Return>", lambda e: self._apri_selezionato())

    def _apri_selezionato(self):
        sel = self.lista.selection()
        if sel:
            self.risultato = (self.archivi[int(sel[0])]["percorso"], None)
            self.root.destroy()

    def _crea(self):
        percorso = filedialog.asksaveasfilename(
            parent=self.root,
            title="Crea un nuovo archivio",
            initialdir=self.cartella,
            initialfile=NOME_PREDEFINITO if not os.path.exists(os.path.join(self.cartella, NOME_PREDEFINITO))
            else "contabilino-nuovo.db",
            defaultextension=".db",
            filetypes=[("Archivio di Contabilino", "*.db"), ("Tutti i file", "*.*")],
        )
        if not percorso:
            return
        if os.path.exists(percorso):
            messagebox.showerror(
                "Archivio già esistente",
                "Esiste già un file con questo nome: scegline un altro.\n"
                "(Per usare un archivio esistente scegli \"Apri\".)",
                parent=self.root,
            )
            return
        piano = chiedi_piano(self.root)
        if not piano:
            return
        self.risultato = (percorso, piano)
        self.root.destroy()

    def _apri_altro(self):
        percorso = filedialog.askopenfilename(
            parent=self.root,
            title="Apri un archivio di Contabilino",
            initialdir=self.cartella,
            filetypes=[("Archivio di Contabilino", "*.db"), ("Tutti i file", "*.*")],
        )
        if not percorso:
            return
        if not info_archivio(percorso):
            messagebox.showerror("File non valido", messaggio_non_valido(percorso), parent=self.root)
            return
        self.risultato = (percorso, None)
        self.root.destroy()

    def mostra(self):
        self.root.mainloop()
        return self.risultato


class SceltaPianoDialog(tk.Toplevel):
    """Piano dei conti del nuovo archivio: semplice (come sempre) o completo per IVA e bilancio."""

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.title("Nuovo archivio")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        f = ttk.Frame(self, padding=(px(22), px(18)))
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="Con quale piano dei conti cominci?", style="Sottotitolo.TLabel").pack(anchor=tk.W)
        self._scelta = tk.StringVar(value="semplice")
        for valore, titolo, testo in (
            ("semplice", "Semplice",
             "I 6 conti di base (cassa, banca, crediti, debiti, costi, ricavi) da completare con i tuoi "
             "sottoconti. Va bene per una contabilità essenziale, come nelle versioni precedenti."),
            ("completo", "Completo, per IVA e bilancio civilistico",
             "Circa 200 conti per una piccola società o ditta (immobilizzazioni e ammortamenti, IVA, "
             "personale, imposte...), già collegati alle voci del bilancio, con la gestione IVA e il "
             "bilancio attivati. Si possono modificare, aggiungere o togliere."),
        ):
            ttk.Radiobutton(f, text=titolo, value=valore, variable=self._scelta).pack(anchor=tk.W, pady=(px(12), 0))
            ttk.Label(f, text=testo, wraplength=px(440), justify=tk.LEFT,
                      style="Secondario.TLabel").pack(anchor=tk.W, padx=(px(26), 0))
        ttk.Label(f, text="IVA e bilancio si possono attivare anche in seguito, da Strumenti > Moduli.",
                  style="Nota.TLabel").pack(anchor=tk.W, pady=(px(14), 0))
        btn = ttk.Frame(f)
        btn.pack(fill=tk.X, pady=(px(14), 0))
        ttk.Button(btn, text="Crea l'archivio", style="Accent.TButton", command=self._ok).pack(side=tk.RIGHT)
        ttk.Button(btn, text="Annulla", command=self.destroy).pack(side=tk.RIGHT, padx=px(6))
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _ok(self):
        self.result = self._scelta.get()
        self.destroy()


def chiedi_piano(parent):
    """ "semplice", "completo" oppure None se l'utente annulla."""
    dlg = SceltaPianoDialog(parent)
    parent.wait_window(dlg)
    return dlg.result


def messaggio_non_valido(percorso):
    return (f"Il file\n{os.path.basename(percorso)}\nnon è un archivio di Contabilino.\n\n"
            "Scegli un file .db creato con Contabilino.")


def scegli_archivio(cartella):
    """
    Archivio da aprire all'avvio: (percorso, piano) con piano None per un archivio
    esistente e "semplice"/"completo" per uno nuovo; None se l'utente esce.
    Se nella cartella c'è contabilino.db, lo apre subito (l'uso di tutti i giorni).
    """
    predefinito = os.path.join(cartella, NOME_PREDEFINITO)
    if os.path.exists(predefinito) and info_archivio(predefinito):
        return predefinito, None
    return FinestraAvvio(cartella, archivi_nella_cartella(cartella)).mostra()
