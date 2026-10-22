"""
Contabilino - Finestra principale
Editing inline nel libro giornale, Tab per navigare, ricerca conti con tastiera.
Le registrazioni si possono correggere, eliminare o stornare.
"""

import os
import sqlite3
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox, filedialog
from datetime import date
from dialogs import (
    EliminaRegistrazioneDialog,
    GestioneContiDialog,
    GestioneEserciziDialog,
    SelezioneContiDialog,
    StornoDialog,
)
import tema
from tema import px
from widgets import SmartDateEntry, AmountEntry, AutocompleteEntry, format_importo
from export import FORMATI, conti_economici, crea_report, salva_report
from version import MANUALE, REPOSITORY, VERSIONE
from dateutils import (
    data_in_periodo,
    etichetta_anni,
    format_display as format_date_display,
    periodo_label,
)


class MainWindow:
    _TITOLO_NUOVA = "Nuova registrazione  (Tab = prossimo campo, Enter = salva)"
    # tipo di report → (voce del menu Export, inizio del nome file proposto)
    _EXPORT = {
        "giornale": ("Libro Giornale", "giornale"),
        "saldi": ("Saldi Conti", "saldi"),
        "costi_ricavi": ("Costi e Ricavi", "costi_ricavi"),
        "partitari": ("Partitari", "partitari"),
    }

    def __init__(self, root, db):
        self.root = root
        self.db = db
        self.esercizio_id = None
        self.esercizio_info = ""

        self.root.title("Contabilino")
        self.root.geometry(f"{px(1040)}x{px(680)}")
        self.root.minsize(px(860), px(560))

        self._conti_map = {}  # "codice - nome" → id
        self._conti_labels = []
        self._modifica_id = None  # registrazione caricata nella riga di input per correggerla
        self._selezioni_export = {}  # tipo di report → ultima scelta dei conti (in questa sessione)
        # Sul Mac il tasto ⌫ è BackSpace e il tasto destro del mouse è Button-2
        self._aqua = self.root.tk.call("tk", "windowingsystem") == "aqua"

        self._build_menu()
        self._build_info_bar()
        self._build_status_bar()  # prima delle schede: resta visibile anche con la finestra piccola
        self._build_tabs()

        self._refresh_conti_cache()
        self._auto_select_esercizio()

    # --- Cache conti ---

    def _refresh_conti_cache(self):
        conti = self.db.get_conti()
        self._conti_map = {}
        self._conti_labels = []
        for c in conti:
            label = f"{c['codice']} - {c['nome']}"
            self._conti_map[label] = c["id"]
            self._conti_labels.append(label)
        # Aggiorna i widget autocomplete se esistono
        if hasattr(self, "_input_dare"):
            self._input_dare.set_values(self._conti_labels)
            self._input_avere.set_values(self._conti_labels)

    def _refresh_causali_cache(self):
        causali = self.db.get_causali_usate(self.esercizio_id)
        if hasattr(self, "_input_causale"):
            self._input_causale.set_values(causali)

    # --- Menu ---

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Nuovo Database...", command=self._on_nuovo_db)
        file_menu.add_command(label="Apri Database...", command=self._on_apri_db)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        esercizio_menu = tk.Menu(menubar, tearoff=0)
        esercizio_menu.add_command(label="Gestione Esercizi...", command=self._on_gestione_esercizi)
        esercizio_menu.add_command(label="Rinumera in ordine di data...", command=self._on_rinumera)
        menubar.add_cascade(label="Esercizio", menu=esercizio_menu)

        conti_menu = tk.Menu(menubar, tearoff=0)
        conti_menu.add_command(label="Gestione Piano dei Conti...", command=self._on_gestione_conti)
        menubar.add_cascade(label="Conti", menu=conti_menu)

        # Export: un sottomenu per report, con i tre formati
        export_menu = tk.Menu(menubar, tearoff=0)
        for tipo in ("giornale", "saldi", None, "costi_ricavi", "partitari"):
            if tipo is None:
                export_menu.add_separator()
                continue
            formati_menu = tk.Menu(export_menu, tearoff=0)
            for formato, (nome_formato, _ext) in FORMATI.items():
                formati_menu.add_command(
                    label=f"{nome_formato}...",
                    command=lambda t=tipo, f=formato: self._on_export(t, f),
                )
            export_menu.add_cascade(label=self._EXPORT[tipo][0], menu=formati_menu)
        menubar.add_cascade(label="Export", menu=export_menu)

        aiuto_menu = tk.Menu(menubar, tearoff=0)
        aiuto_menu.add_command(label="Manuale online", command=lambda: webbrowser.open(MANUALE))
        aiuto_menu.add_command(label="Informazioni su Contabilino...", command=self._on_informazioni)
        menubar.add_cascade(label="?", menu=aiuto_menu)

        self.root.config(menu=menubar)

    # --- Info bar ---

    def _build_info_bar(self):
        """Intestazione: logo, nome del programma ed esercizio attivo."""
        self.info_frame = ttk.Frame(self.root, padding=(px(18), px(14), px(18), px(6)))
        self.info_frame.pack(fill=tk.X)

        self._logo = tema.logo(self.root, 48 if tema.SCALA >= 1.4 else 32)
        ttk.Label(self.info_frame, image=self._logo).pack(side=tk.LEFT)
        titoli = ttk.Frame(self.info_frame)
        titoli.pack(side=tk.LEFT, padx=(px(10), 0))
        ttk.Label(titoli, text="Contabilino", style="Titolo.TLabel").pack(anchor=tk.W)
        self.esercizio_label = ttk.Label(titoli, text="Nessun esercizio selezionato", style="Secondario.TLabel")
        self.esercizio_label.pack(anchor=tk.W)

        ttk.Button(self.info_frame, text="Esercizi...", command=self._on_gestione_esercizi).pack(side=tk.RIGHT)

    # --- Tabs ---

    def _build_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=px(18), pady=(px(6), px(10)))

        self.giornale_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.giornale_frame, text="Libro Giornale")
        self._build_giornale_tab()

        self.saldi_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.saldi_frame, text="Saldi Conti")
        self._build_saldi_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _build_giornale_tab(self):
        # Treeview - layout compatto: una riga per registrazione
        tree_frame = ttk.Frame(self.giornale_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=px(12), pady=(px(12), 0))

        cols = ("numero", "data", "causale", "dare", "avere", "importo")
        self.giornale_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        self.giornale_tree.heading("numero", text="N.")
        self.giornale_tree.heading("data", text="Data")
        self.giornale_tree.heading("causale", text="Causale")
        self.giornale_tree.heading("dare", text="Conto Dare")
        self.giornale_tree.heading("avere", text="Conto Avere")
        self.giornale_tree.heading("importo", text="Importo")

        self.giornale_tree.column("numero", width=px(50), anchor=tk.CENTER, stretch=False)
        self.giornale_tree.column("data", width=px(100), anchor=tk.CENTER, stretch=False)
        self.giornale_tree.column("causale", width=px(260))
        self.giornale_tree.column("dare", width=px(200))
        self.giornale_tree.column("avere", width=px(200))
        self.giornale_tree.column("importo", width=px(110), anchor=tk.E, stretch=False)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.giornale_tree.yview)
        self.giornale_tree.configure(yscrollcommand=scrollbar.set)
        self.giornale_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Comandi sulla registrazione selezionata: tastiera, doppio clic, tasto destro
        self.giornale_tree.bind("<Delete>", lambda e: self._on_elimina_registrazione())
        self.giornale_tree.bind("<Return>", lambda e: self._on_modifica_registrazione())
        self.giornale_tree.bind("<Double-Button-1>", self._on_doppio_clic_giornale)
        self.giornale_tree.bind("<<TreeviewSelect>>", lambda e: self._aggiorna_azioni())
        tasti_menu = ["<Button-3>"]
        if self._aqua:
            self.giornale_tree.bind("<BackSpace>", lambda e: self._on_elimina_registrazione())
            tasti_menu += ["<Button-2>", "<Control-Button-1>"]
        for tasto in tasti_menu:
            self.giornale_tree.bind(tasto, self._on_menu_giornale)

        self._menu_giornale = tk.Menu(self.giornale_tree, tearoff=0)
        self._menu_giornale.add_command(label="Modifica", accelerator="Invio",
                                        command=self._on_modifica_registrazione)
        self._menu_giornale.add_command(label="Elimina...", accelerator="⌫" if self._aqua else "Canc",
                                        command=self._on_elimina_registrazione)
        self._menu_giornale.add_command(label="Storno...", command=self._on_storno_registrazione)

        azioni_frame = ttk.Frame(self.giornale_frame)
        azioni_frame.pack(fill=tk.X, padx=px(12), pady=(px(8), 0))
        ttk.Label(azioni_frame, text="Registrazione selezionata", style="Secondario.TLabel").pack(side=tk.LEFT, padx=(0, px(8)))
        self._btn_modifica = ttk.Button(azioni_frame, text="Modifica", command=self._on_modifica_registrazione)
        self._btn_elimina = ttk.Button(azioni_frame, text="Elimina...", command=self._on_elimina_registrazione)
        self._btn_storno = ttk.Button(azioni_frame, text="Storno...", command=self._on_storno_registrazione)
        for btn in (self._btn_modifica, self._btn_elimina, self._btn_storno):
            btn.pack(side=tk.LEFT, padx=(0, px(6)))

        # --- Riga di input inline ---
        self._build_input_row()

    def _build_input_row(self):
        input_frame = ttk.LabelFrame(self.giornale_frame, text=self._TITOLO_NUOVA, padding=(px(12), px(8), px(12), px(12)))
        input_frame.pack(fill=tk.X, padx=px(12), pady=px(12))
        self._input_frame = input_frame

        # Griglia di input
        for col, testo in enumerate(("Data", "Causale", "Conto Dare", "Conto Avere", "Importo")):
            ttk.Label(input_frame, text=testo, style="Secondario.TLabel").grid(
                row=0, column=col, padx=px(3), pady=(0, px(3)), sticky=tk.W
            )

        self._input_data = SmartDateEntry(input_frame, width=12)
        self._input_data.grid(row=1, column=0, padx=px(3), sticky=tk.W + tk.E)

        self._input_causale = AutocompleteEntry(input_frame, values=[], allow_free_text=True, width=25)
        self._input_causale.grid(row=1, column=1, padx=px(3), sticky=tk.W + tk.E)

        self._input_dare = AutocompleteEntry(input_frame, values=self._conti_labels, width=22)
        self._input_dare.grid(row=1, column=2, padx=px(3), sticky=tk.W + tk.E)

        self._input_avere = AutocompleteEntry(input_frame, values=self._conti_labels, width=22)
        self._input_avere.grid(row=1, column=3, padx=px(3), sticky=tk.W + tk.E)

        self._input_importo = AmountEntry(input_frame, width=12)
        self._input_importo.grid(row=1, column=4, padx=px(3), sticky=tk.W + tk.E)

        # Enter sull'importo → salva
        self._input_importo.bind("<Return>", lambda e: self._salva_registrazione_inline())

        # Pulsanti
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=1, column=5, padx=(px(10), 0))
        ttk.Button(btn_frame, text="Salva", width=8, style="Accent.TButton",
                   command=self._salva_registrazione_inline).pack(side=tk.LEFT, padx=(0, px(6)))
        # Durante una modifica diventa "Annulla"
        self._btn_pulisci = ttk.Button(btn_frame, text="Pulisci", width=8, command=self._clear_input_row)
        self._btn_pulisci.pack(side=tk.LEFT)

        # Configura colonne per espansione
        input_frame.columnconfigure(1, weight=2)
        input_frame.columnconfigure(2, weight=1)
        input_frame.columnconfigure(3, weight=1)

        # Escape pulisce
        for widget in (self._input_data, self._input_causale,
                       self._input_dare, self._input_avere, self._input_importo):
            widget.bind("<Escape>", lambda e: self._clear_input_row())

    def _clear_input_row(self):
        """Svuota la riga di input; se era in corso una modifica, la annulla."""
        self._modifica_id = None
        self._aggiorna_titolo_input()
        self._input_data.clear()
        self._input_causale.clear()
        self._input_dare.clear()
        self._input_avere.clear()
        self._input_importo.clear()
        self._input_data.focus_set()

    def _aggiorna_titolo_input(self):
        """Titolo della riga di input: nuova registrazione, oppure modifica della n. X."""
        if self._modifica_id:
            numero = self.db.get_registrazione_compatta(self._modifica_id)["numero"]
            self._input_frame.config(
                text=f"Modifica registrazione n. {numero}  (Enter = salva le modifiche, Esc = annulla)"
            )
            self._btn_pulisci.config(text="Annulla")
        else:
            self._input_frame.config(text=self._TITOLO_NUOVA)
            self._btn_pulisci.config(text="Pulisci")

    def _salva_registrazione_inline(self):
        if not self.esercizio_id:
            messagebox.showwarning("Attenzione", "Selezionare prima un esercizio.")
            return

        esercizio = self.db.get_esercizio(self.esercizio_id)
        if esercizio["data_chiusura"]:
            messagebox.showwarning("Attenzione", "L'esercizio selezionato è chiuso.")
            return

        # Formatta la data prima di leggere
        self._input_data._format()

        data = self._input_data.get_iso_date()
        causale = self._input_causale.get_value()
        dare_label = self._input_dare.get_value()
        avere_label = self._input_avere.get_value()
        importo = self._input_importo.get_amount()

        # Validazione
        if not data:
            self.status_var.set("Inserire una data valida (GG/MM/AAAA).")
            self._input_data.focus_set()
            return
        if not data_in_periodo(data, esercizio["data_inizio"], esercizio["data_fine"]):
            periodo = periodo_label(esercizio["data_inizio"], esercizio["data_fine"])
            messagebox.showwarning(
                "Data fuori esercizio",
                f"La data {format_date_display(data)} non rientra nell'esercizio\n"
                f"{esercizio['descrizione']} ({periodo}).",
            )
            self.status_var.set(f"Data fuori dall'esercizio ({periodo}).")
            self._input_data.focus_set()
            return
        if not causale:
            self.status_var.set("Inserire la causale.")
            self._input_causale.focus_set()
            return
        if dare_label not in self._conti_map:
            self.status_var.set("Conto Dare non valido. Selezionare dalla lista.")
            self._input_dare.focus_set()
            return
        if avere_label not in self._conti_map:
            self.status_var.set("Conto Avere non valido. Selezionare dalla lista.")
            self._input_avere.focus_set()
            return
        if importo <= 0:
            self.status_var.set("Inserire un importo maggiore di zero.")
            self._input_importo.focus_set()
            return

        dare_id = self._conti_map[dare_label]
        avere_id = self._conti_map[avere_label]

        if dare_id == avere_id:
            self.status_var.set("I conti Dare e Avere devono essere diversi.")
            self._input_dare.focus_set()
            return

        movimenti = [
            (dare_id, importo, 0),
            (avere_id, 0, importo),
        ]
        fuori_ordine_prima = self.db.conta_numeri_fuori_ordine(self.esercizio_id)
        try:
            if self._modifica_id:
                reg_id = self._modifica_id
                self.db.modifica_registrazione(reg_id, data, causale, movimenti)
                numero = self.db.get_registrazione_compatta(reg_id)["numero"]
                messaggio = f"Registrazione n. {numero} modificata: {causale} - {format_importo(importo)}"
            else:
                reg_id = self.db.crea_registrazione(self.esercizio_id, data, causale, movimenti)
                messaggio = f"Registrazione salvata: {causale} - {format_importo(importo)}"
        except ValueError as e:
            messagebox.showerror("Errore", str(e))
            return
        except sqlite3.Error as e:
            # Es. database su chiavetta scollegata o bloccato da un altro programma:
            # la registrazione non è stata salvata (né in parte né del tutto)
            messagebox.showerror(
                "Errore",
                f"Impossibile salvare nel database:\n{e}\n\n"
                "La registrazione NON è stata salvata: controlla che il file sia\n"
                "raggiungibile e non aperto in un altro programma, poi riprova.",
            )
            return

        self._refresh_giornale()
        self._refresh_causali_cache()
        self.status_var.set(messaggio)
        self._clear_input_row()

        # Mostra la registrazione salvata (l'ordine è per data: non è per forza l'ultima)
        self.giornale_tree.selection_set(str(reg_id))
        self.giornale_tree.see(str(reg_id))

        # Data precedente a registrazioni con numero più basso: i numeri non seguono più le date
        if self.db.conta_numeri_fuori_ordine(self.esercizio_id) > fuori_ordine_prima:
            numero = self.db.get_registrazione_compatta(reg_id)["numero"]
            self._chiedi_rinumerazione(
                f"La registrazione n. {numero} del {format_date_display(data)} ha una data\n"
                "precedente a registrazioni con un numero più basso: nel giornale\n"
                "i numeri non sono più in ordine di data.\n\n",
                seleziona=reg_id,
            )

    def _build_saldi_tab(self):
        tree_frame = ttk.Frame(self.saldi_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=px(12), pady=(px(12), px(6)))

        cols = ("codice", "nome", "tipo", "dare", "avere", "saldo")
        self.saldi_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        self.saldi_tree.heading("codice", text="Codice")
        self.saldi_tree.heading("nome", text="Conto")
        self.saldi_tree.heading("tipo", text="Tipo")
        self.saldi_tree.heading("dare", text="Tot. Dare")
        self.saldi_tree.heading("avere", text="Tot. Avere")
        self.saldi_tree.heading("saldo", text="Saldo")

        self.saldi_tree.column("codice", width=px(80), anchor=tk.CENTER, stretch=False)
        self.saldi_tree.column("nome", width=px(280))
        self.saldi_tree.column("tipo", width=px(90), anchor=tk.CENTER, stretch=False)
        self.saldi_tree.column("dare", width=px(130), anchor=tk.E, stretch=False)
        self.saldi_tree.column("avere", width=px(130), anchor=tk.E, stretch=False)
        self.saldi_tree.column("saldo", width=px(130), anchor=tk.E, stretch=False)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.saldi_tree.yview)
        self.saldi_tree.configure(yscrollcommand=scrollbar.set)
        self.saldi_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.totali_frame = ttk.Frame(self.saldi_frame)
        self.totali_frame.pack(fill=tk.X, padx=px(12), pady=(0, px(12)))
        self.totali_label = ttk.Label(self.totali_frame, text="", style="Forte.TLabel")
        self.totali_label.pack(side=tk.RIGHT)

    # --- Status bar ---

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Pronto. Tab per navigare, Enter per salvare.")
        barra = ttk.Frame(self.root)
        barra.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Separator(barra, orient=tk.HORIZONTAL).pack(fill=tk.X)
        self.db_label = ttk.Label(barra, text=self._testo_db(self.db.db_path), style="Stato.TLabel")
        self.db_label.pack(side=tk.RIGHT)
        ttk.Label(barra, textvariable=self.status_var, anchor=tk.W, style="Stato.TLabel").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

    @staticmethod
    def _testo_db(percorso):
        """Nome del file di database nella barra di stato (il percorso completo è troppo lungo)."""
        return f"Archivio: {os.path.basename(percorso)}"

    # --- Esercizio ---

    def _auto_select_esercizio(self):
        """Sceglie l'esercizio che contiene la data odierna; altrimenti il primo aperto."""
        oggi = self.db.get_esercizio_per_data(date.today().isoformat())
        if oggi and not oggi["data_chiusura"]:
            self._set_esercizio(oggi["id"])
            return
        esercizi = self.db.get_esercizi()
        for e in esercizi:
            if not e["data_chiusura"]:
                self._set_esercizio(e["id"])
                return
        if oggi:
            self._set_esercizio(oggi["id"])
        elif esercizi:
            self._set_esercizio(esercizi[0]["id"])
        else:
            self._set_esercizio(None)

    def _set_esercizio(self, esercizio_id):
        if self._modifica_id and esercizio_id != self.esercizio_id:
            self._clear_input_row()  # la modifica in corso riguardava l'altro esercizio
        self.esercizio_id = esercizio_id
        if esercizio_id:
            e = self.db.get_esercizio(esercizio_id)
            stato = "Chiuso" if e["data_chiusura"] else "Aperto"
            periodo = periodo_label(e["data_inizio"], e["data_fine"])
            self.esercizio_info = f"{e['descrizione']}  {periodo}  ({stato})"
            self.esercizio_label.config(text=f"{e['descrizione']}  ·  {periodo}  ·  {stato}")
        else:
            self.esercizio_info = ""
            self.esercizio_label.config(text="Nessun esercizio selezionato")
        self._refresh_giornale()
        self._refresh_saldi()
        self._refresh_causali_cache()

    # --- Refresh dati ---

    def _refresh_giornale(self):
        for item in self.giornale_tree.get_children():
            self.giornale_tree.delete(item)
        self._aggiorna_azioni()  # la selezione è sparita insieme alle righe
        if not self.esercizio_id:
            return
        rows = self.db.get_registrazioni_compatte(self.esercizio_id)
        for row in rows:
            dare_str = f"{row['dare_codice']} - {row['dare_nome']}"
            avere_str = f"{row['avere_codice']} - {row['avere_nome']}"
            importo_str = format_importo(row["importo"])
            data_str = format_date_display(row["data"])
            self.giornale_tree.insert(
                "", tk.END,
                iid=str(row["id"]),
                values=(row["numero"], data_str, row["descrizione"],
                        dare_str, avere_str, importo_str),
            )

    def _refresh_saldi(self):
        for item in self.saldi_tree.get_children():
            self.saldi_tree.delete(item)
        if not self.esercizio_id:
            self.totali_label.config(text="")
            return
        rows = self.db.get_saldi(self.esercizio_id)
        tot_dare = 0
        tot_avere = 0
        for row in rows:
            dare = row["totale_dare"]
            avere = row["totale_avere"]
            saldo = dare - avere
            tot_dare += dare
            tot_avere += avere
            # Indenta i sottoconti
            nome = row["nome"]
            if row["padre_id"]:
                nome = "    " + nome
            self.saldi_tree.insert(
                "", tk.END,
                values=(row["codice"], nome, row["tipo"],
                        format_importo(dare) or "0,00",
                        format_importo(avere) or "0,00",
                        format_importo(saldo) or "0,00"),
            )
        diff = tot_dare - tot_avere
        self.totali_label.config(
            text=f"Totale Dare: {format_importo(tot_dare) or '0,00'}  |  "
                 f"Totale Avere: {format_importo(tot_avere) or '0,00'}  |  "
                 f"Differenza: {format_importo(diff) or '0,00'}"
        )

    def _on_tab_changed(self, event=None):
        idx = self.notebook.index(self.notebook.select())
        if idx == 1:
            self._refresh_saldi()

    # --- Azioni menu ---

    def _on_nuovo_db(self):
        filepath = filedialog.asksaveasfilename(
            title="Crea nuovo database",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("Tutti i file", "*.*")],
        )
        if filepath:
            self._switch_db(filepath, new=True)

    def _on_apri_db(self):
        filepath = filedialog.askopenfilename(
            title="Apri database esistente",
            filetypes=[("SQLite Database", "*.db"), ("Tutti i file", "*.*")],
        )
        if filepath:
            self._switch_db(filepath, new=False)

    def _switch_db(self, filepath, new=False):
        self.db.close()
        self.db.db_path = filepath
        self.db.backup_path = None
        self.db.connect()
        if new:
            self.db.init_db()
        else:
            self.db.create_tables()
        if self.db.backup_path:
            messagebox.showinfo(
                "Database aggiornato",
                "Il database è stato aggiornato al nuovo formato degli esercizi\n"
                "(periodo con data di inizio e data di fine).\n\n"
                "Gli esercizi esistenti sono diventati periodi 01/01 - 31/12.\n"
                f"Copia di sicurezza del database precedente:\n{self.db.backup_path}",
            )
        self.db_label.config(text=self._testo_db(filepath))
        if self._modifica_id:
            self._clear_input_row()  # la registrazione in modifica era dell'altro database
        self._selezioni_export = {}  # i conti scelti erano dell'altro database
        self._refresh_conti_cache()
        self.esercizio_id = None
        self._auto_select_esercizio()
        self.status_var.set(f"Database {'creato' if new else 'aperto'}: {filepath}")

    def _on_gestione_esercizi(self):
        dlg = GestioneEserciziDialog(self.root, self.db, self.esercizio_id)
        self.root.wait_window(dlg)
        # Sempre: l'esercizio corrente può essere stato modificato o eliminato
        if dlg.selected_id and not self.db.get_esercizio(dlg.selected_id):
            self._auto_select_esercizio()
        else:
            self._set_esercizio(dlg.selected_id)

    def _on_informazioni(self):
        messagebox.showinfo(
            "Informazioni su Contabilino",
            f"Contabilino {VERSIONE}\n"
            "Contabilità in partita doppia per piccole attività.\n\n"
            "Software libero, distribuito con licenza GNU GPL v3:\n"
            "puoi usarlo, studiarlo, modificarlo e ridistribuirlo.\n"
            "È fornito così com'è, senza alcuna garanzia.\n\n"
            f"Manuale: {MANUALE}\n"
            f"Codice sorgente: {REPOSITORY}",
        )

    def _on_rinumera(self):
        if not self.esercizio_id:
            messagebox.showwarning("Attenzione", "Selezionare prima un esercizio.")
            return
        esercizio = self.db.get_esercizio(self.esercizio_id)
        if esercizio["data_chiusura"]:
            messagebox.showwarning(
                "Esercizio chiuso",
                f"L'esercizio \"{esercizio['descrizione']}\" è chiuso: la numerazione non si può cambiare.",
            )
            return
        if not self.db.conta_numeri_fuori_ordine(self.esercizio_id):
            messagebox.showinfo("Numerazione", "Le registrazioni sono già numerate in ordine di data.")
            return
        self._chiedi_rinumerazione("")

    def _chiedi_rinumerazione(self, premessa, seleziona=None):
        """Chiede se rinumerare le registrazioni dell'esercizio in ordine di data, e lo fa."""
        n = self.db.conta_numeri_fuori_ordine(self.esercizio_id)
        if not messagebox.askyesno(
            "Rinumerare in ordine di data?",
            premessa
            + f"Rinumerare le registrazioni dell'esercizio in ordine di data?\n"
            f"Cambia il numero di {n} registrazion{'e' if n == 1 else 'i'}.\n\n"
            "Attenzione: i numeri già stampati o esportati non corrisponderanno più,\n"
            "e i numeri citati nelle causali (es. \"Storno reg. n. ...\") non cambiano.",
        ):
            return
        try:
            cambiate = self.db.rinumera_in_ordine_di_data(self.esercizio_id)
        except ValueError as e:
            messagebox.showerror("Errore", str(e))
            return
        if self._modifica_id:
            self._aggiorna_titolo_input()
        self._refresh_giornale()
        if seleziona:
            self.giornale_tree.selection_set(str(seleziona))
            self.giornale_tree.see(str(seleziona))
        self.status_var.set(f"Registrazioni rinumerate in ordine di data ({cambiate} numeri cambiati).")

    def _on_gestione_conti(self):
        GestioneContiDialog(self.root, self.db)
        self._refresh_conti_cache()
        self._refresh_giornale()
        self._refresh_saldi()

    # --- Registrazione selezionata: modifica, eliminazione, storno ---

    def _aggiorna_azioni(self):
        """I pulsanti sulla registrazione sono attivi solo se c'è una riga selezionata."""
        stato = tk.NORMAL if self.giornale_tree.selection() else tk.DISABLED
        for btn in (self._btn_modifica, self._btn_elimina, self._btn_storno):
            btn.config(state=stato)

    def _on_doppio_clic_giornale(self, event):
        # Solo sulle righe, non sulle intestazioni delle colonne
        if self.giornale_tree.identify_region(event.x, event.y) == "cell":
            self._on_modifica_registrazione()

    def _on_menu_giornale(self, event):
        """Tasto destro: seleziona la riga sotto il mouse e mostra i comandi."""
        riga = self.giornale_tree.identify_row(event.y)
        if not riga:
            return
        self.giornale_tree.selection_set(riga)
        self.giornale_tree.focus(riga)
        try:
            self._menu_giornale.tk_popup(event.x_root, event.y_root)
        finally:
            self._menu_giornale.grab_release()
        return "break"

    def _registrazione_selezionata(self):
        """Dati completi della registrazione selezionata nel giornale (None se nessuna)."""
        sel = self.giornale_tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Selezionare una registrazione nel Libro Giornale.")
            return None
        return self.db.get_registrazione_compatta(int(sel[0]))

    def _on_modifica_registrazione(self):
        """Carica la registrazione selezionata nella riga di input per correggerla."""
        reg = self._registrazione_selezionata()
        if not reg:
            return
        esercizio = self.db.get_esercizio(reg["esercizio_id"])
        if esercizio["data_chiusura"]:
            messagebox.showwarning(
                "Esercizio chiuso",
                f"L'esercizio \"{esercizio['descrizione']}\" è chiuso: le sue registrazioni\n"
                "non si possono modificare. Per correggerle riaprilo da\n"
                "Esercizio > Gestione Esercizi, oppure usa lo Storno.",
            )
            return
        self._clear_input_row()
        self._modifica_id = reg["id"]
        self._aggiorna_titolo_input()
        self._input_data.set_iso_date(reg["data"])
        self._input_causale.set_value(reg["descrizione"])
        self._input_dare.set_value(f"{reg['dare_codice']} - {reg['dare_nome']}")
        self._input_avere.set_value(f"{reg['avere_codice']} - {reg['avere_nome']}")
        self._input_importo.set_amount(reg["importo"])
        self._input_data.focus_set()
        self.status_var.set(
            f"Modifica della registrazione n. {reg['numero']}: correggi i campi e premi Salva "
            "(o Enter sull'importo). Esc per annullare."
        )

    def _on_elimina_registrazione(self):
        reg = self._registrazione_selezionata()
        if not reg:
            return
        esercizio = self.db.get_esercizio(reg["esercizio_id"])
        if esercizio["data_chiusura"]:
            if messagebox.askyesno(
                "Esercizio chiuso",
                f"L'esercizio \"{esercizio['descrizione']}\" è chiuso: le sue registrazioni\n"
                "non si possono eliminare (per farlo va prima riaperto da\n"
                "Esercizio > Gestione Esercizi).\n\n"
                "Vuoi invece registrare uno storno in un esercizio aperto?",
            ):
                self._storna(reg)
            return

        successive = self.db.conta_registrazioni_successive(reg["esercizio_id"], reg["numero"])
        dlg = EliminaRegistrazioneDialog(self.root, reg, successive)
        self.root.wait_window(dlg)
        if dlg.result == "storno":
            self._storna(reg)
            return
        if dlg.result != "elimina":
            return

        try:
            self.db.elimina_registrazione(reg["id"], rinumera=dlg.rinumera)
        except ValueError as e:
            messagebox.showerror("Errore", str(e))
            return
        if self._modifica_id == reg["id"]:
            self._clear_input_row()
        elif self._modifica_id:
            self._aggiorna_titolo_input()  # la rinumerazione può averne cambiato il numero
        self._refresh_giornale()
        self._refresh_saldi()
        self._refresh_causali_cache()
        messaggio = f"Registrazione n. {reg['numero']} eliminata."
        if dlg.rinumera:
            messaggio += " Le registrazioni successive sono state rinumerate."
        self.status_var.set(messaggio)

    def _on_storno_registrazione(self):
        reg = self._registrazione_selezionata()
        if reg:
            self._storna(reg)

    def _storna(self, reg):
        """Dialogo di storno; poi mostra dov'è finita la nuova registrazione."""
        dlg = StornoDialog(self.root, self.db, reg)
        self.root.wait_window(dlg)
        if not dlg.result:
            return
        storno = self.db.get_registrazione_compatta(dlg.result)
        riferimento = f"n. {storno['numero']} del {format_date_display(storno['data'])}"
        if storno["esercizio_id"] == self.esercizio_id:
            self._refresh_giornale()
            self._refresh_saldi()
            self._refresh_causali_cache()
            self.giornale_tree.selection_set(str(storno["id"]))
            self.giornale_tree.see(str(storno["id"]))
            self.status_var.set(
                f"Storno della registrazione n. {reg['numero']} registrato come {riferimento}."
            )
        else:
            # Lo storno è finito in un altro esercizio: non si vede nel giornale attuale
            esercizio = self.db.get_esercizio(storno["esercizio_id"])
            messagebox.showinfo(
                "Storno registrato",
                f"Lo storno è stato registrato nell'esercizio \"{esercizio['descrizione']}\"\n"
                f"come {riferimento}.\n\n"
                "Per vederlo seleziona quell'esercizio da Esercizio > Gestione Esercizi.",
            )
            self.status_var.set(
                f"Storno registrato in \"{esercizio['descrizione']}\" come {riferimento}."
            )

    def _on_export(self, tipo, formato):
        if not self.esercizio_id:
            messagebox.showwarning("Attenzione", "Selezionare prima un esercizio.")
            return

        tipo_label, nome_base = self._EXPORT[tipo]
        nome_formato, ext = FORMATI[formato]
        esercizio = self.db.get_esercizio(self.esercizio_id)

        # Saldi, costi e ricavi, partitari: tutti i conti oppure solo quelli scelti
        opzioni = {}
        if tipo != "giornale":
            conti = conti_economici(self.db) if tipo == "costi_ricavi" else self.db.get_conti()
            dlg = SelezioneContiDialog(
                self.root, conti, tipo_label, self._selezioni_export.get(tipo),
                solo_economici=(tipo == "partitari"),
            )
            self.root.wait_window(dlg)
            if not dlg.result:
                return
            self._selezioni_export[tipo] = dlg.scelta
            if dlg.scelta == "economici":
                opzioni["conto_ids"] = dlg.result
                nome_base = f"{nome_base}_costi_ricavi"
            elif dlg.result != "tutti":
                opzioni["conto_ids"] = dlg.result
                if len(dlg.result) == 1:
                    codice = next(c["codice"] for c in conti if c["id"] == dlg.result[0])
                    nome_base = f"{nome_base}_{codice}"
                else:
                    nome_base = f"{nome_base}_selezione"

        report = crea_report(self.db, self.esercizio_id, tipo, **opzioni)
        if opzioni and self._selezioni_export.get(tipo) == "economici":
            report.filtro = "Selezione: conti di costo e ricavo"
        if report.vuoto and tipo != "giornale":
            messagebox.showinfo(
                "Export",
                f"Nell'esercizio \"{esercizio['descrizione']}\" non ci sono movimenti\n"
                "sui conti scelti: niente da esportare.",
            )
            return

        filepath = filedialog.asksaveasfilename(
            title=f"Esporta {tipo_label} ({nome_formato})",
            defaultextension=ext,
            filetypes=[(nome_formato, f"*{ext}")],
            initialfile=f"{nome_base}_{etichetta_anni(esercizio['data_inizio'], esercizio['data_fine'])}{ext}",
        )
        if not filepath:
            return

        try:
            salva_report(report, filepath, formato)
            self.status_var.set(f"{tipo_label} esportato: {filepath}")
            messagebox.showinfo("Export", f"{tipo_label} esportato in:\n{filepath}")
        except ImportError:
            modulo = "openpyxl" if formato == "xlsx" else "reportlab"
            messagebox.showerror(
                "Errore",
                f"Per l'export {nome_formato} è necessario installare {modulo}:\npip install {modulo}",
            )
        except PermissionError:
            messagebox.showerror(
                "Errore",
                f"Impossibile scrivere il file:\n{filepath}\n\n"
                "Se è aperto in un altro programma (Excel, lettore PDF), chiudilo e riprova.",
            )
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'export:\n{e}")
