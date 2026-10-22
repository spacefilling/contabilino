"""
Contabilino - Finestra principale
Editing inline nel libro giornale, Tab per navigare, ricerca conti con tastiera.
Le registrazioni si possono correggere, eliminare o stornare.
"""

import os
import sqlite3
import subprocess
import sys
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox, filedialog
from datetime import date
from dialogs import (
    EliminaRegistrazioneDialog,
    GestioneContiDialog,
    GestioneEserciziDialog,
    RegistrazioneCompostaDialog,
    SelezioneContiDialog,
    StornoDialog,
)
import tema
from avvio import info_archivio, messaggio_non_valido
from tema import px
from widgets import SmartDateEntry, AmountEntry, AutocompleteEntry, format_importo
from export import FORMATI, SEGNO_SALDO, conti_economici, crea_report, movimenti_partitario, salva_report
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
        # Misura comoda, ma mai più grande dello schermo (es. portatile con zoom al 150%)
        schermo_l, schermo_a = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        larghezza = min(px(1040), schermo_l - px(40))
        altezza = min(px(680), schermo_a - px(90))
        x, y = max(0, (schermo_l - larghezza) // 2), max(0, (schermo_a - altezza) // 3)
        self.root.geometry(f"{larghezza}x{altezza}+{x}+{y}")
        self.root.minsize(min(px(860), larghezza), min(px(520), altezza))

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
        if hasattr(self, "_partitario_conto"):
            self._partitario_conto.set_values(self._conti_labels)

    def _refresh_causali_cache(self):
        causali = self.db.get_causali_usate(self.esercizio_id)
        if hasattr(self, "_input_causale"):
            self._input_causale.set_values(causali)

    # --- Menu ---

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Nuovo archivio...", command=self._on_nuovo_db)
        file_menu.add_command(label="Apri archivio...", command=self._on_apri_db)
        file_menu.add_command(label="Mostra la cartella dell'archivio", command=self._on_mostra_cartella)
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

        self.partitario_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.partitario_frame, text="Partitari")
        self._build_partitario_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _build_giornale_tab(self):
        # Treeview - layout compatto: una riga per registrazione
        tree_frame = ttk.Frame(self.giornale_frame)

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
        self.giornale_tree.column("causale", width=px(210))
        self.giornale_tree.column("dare", width=px(170))
        self.giornale_tree.column("avere", width=px(170))
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
        ttk.Label(azioni_frame, text="Registrazione selezionata", style="Secondario.TLabel").pack(side=tk.LEFT, padx=(0, px(8)))
        self._btn_modifica = ttk.Button(azioni_frame, text="Modifica", command=self._on_modifica_registrazione)
        self._btn_elimina = ttk.Button(azioni_frame, text="Elimina...", command=self._on_elimina_registrazione)
        self._btn_storno = ttk.Button(azioni_frame, text="Storno...", command=self._on_storno_registrazione)
        for btn in (self._btn_modifica, self._btn_elimina, self._btn_storno):
            btn.pack(side=tk.LEFT, padx=(0, px(6)))
        ttk.Button(azioni_frame, text="Registrazione composta...",
                   command=self._apri_registrazione_composta).pack(side=tk.RIGHT)

        # --- Riga di input inline ---
        self._build_input_row()

        # Dal basso verso l'alto: se la finestra è bassa si accorcia la tabella,
        # mentre la riga di inserimento e i pulsanti restano sempre visibili
        self._input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=px(12), pady=px(12))
        azioni_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=px(12), pady=(px(8), 0))
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=px(12), pady=(px(12), 0))

    def _build_input_row(self):
        input_frame = ttk.LabelFrame(self.giornale_frame, text=self._TITOLO_NUOVA, padding=(px(12), px(8), px(12), px(12)))
        self._input_frame = input_frame

        # Griglia di input
        for col, testo in enumerate(("Data", "Causale", "Conto Dare", "Conto Avere", "Importo")):
            ttk.Label(input_frame, text=testo, style="Secondario.TLabel").grid(
                row=0, column=col, padx=px(3), pady=(0, px(3)), sticky=tk.W
            )

        self._input_data = SmartDateEntry(input_frame, width=11)
        self._input_data.grid(row=1, column=0, padx=px(3), sticky=tk.W + tk.E)

        self._input_causale = AutocompleteEntry(input_frame, values=[], allow_free_text=True, width=20)
        self._input_causale.grid(row=1, column=1, padx=px(3), sticky=tk.W + tk.E)

        self._input_dare = AutocompleteEntry(input_frame, values=self._conti_labels, width=18)
        self._input_dare.grid(row=1, column=2, padx=px(3), sticky=tk.W + tk.E)

        self._input_avere = AutocompleteEntry(input_frame, values=self._conti_labels, width=18)
        self._input_avere.grid(row=1, column=3, padx=px(3), sticky=tk.W + tk.E)

        self._input_importo = AmountEntry(input_frame, width=11)
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

        # Albero: i sottoconti stanno dentro il loro conto padre, che si apre e si chiude
        cols = ("tipo", "dare", "avere", "saldo")
        self.saldi_tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings")
        self.saldi_tree.heading("#0", text="Conto", anchor=tk.W)
        self.saldi_tree.heading("tipo", text="Tipo")
        self.saldi_tree.heading("dare", text="Tot. Dare")
        self.saldi_tree.heading("avere", text="Tot. Avere")
        self.saldi_tree.heading("saldo", text="Saldo")

        self.saldi_tree.column("#0", width=px(330), minwidth=px(220))
        self.saldi_tree.column("tipo", width=px(90), anchor=tk.CENTER, stretch=False)
        self.saldi_tree.column("dare", width=px(130), anchor=tk.E, stretch=False)
        self.saldi_tree.column("avere", width=px(130), anchor=tk.E, stretch=False)
        self.saldi_tree.column("saldo", width=px(130), anchor=tk.E, stretch=False)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.saldi_tree.yview)
        self.saldi_tree.configure(yscrollcommand=scrollbar.set)
        self.saldi_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.totali_frame = ttk.Frame(self.saldi_frame)
        # Impacchettati prima della tabella: con la finestra bassa i totali restano visibili
        self.totali_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=px(12), pady=(0, px(12)), before=tree_frame)
        self.totali_label = ttk.Label(self.totali_frame, text="", style="Forte.TLabel")
        self.totali_label.pack(side=tk.RIGHT)
        ttk.Button(self.totali_frame, text="Espandi tutto",
                   command=lambda: self._apri_gruppi_saldi(True)).pack(side=tk.LEFT)
        ttk.Button(self.totali_frame, text="Comprimi tutto",
                   command=lambda: self._apri_gruppi_saldi(False)).pack(side=tk.LEFT, padx=(px(6), 0))

        self.saldi_tree.tag_configure("gruppo", font=tema.FONT_FORTE)
        self.saldi_tree.tag_configure("diretto", foreground=tema.TESTO_SECONDARIO)
        self._saldi_chiusi = set()  # conti padre chiusi dall'utente: restano chiusi quando i saldi si aggiornano
        self.saldi_tree.bind("<Double-Button-1>", self._on_doppio_clic_saldi)
        self.saldi_tree.bind("<Return>", lambda e: self._apri_partitario(self.saldi_tree.focus()))
        self.saldi_tree.bind("<<TreeviewClose>>", lambda e: self._saldi_chiusi.add(self.saldi_tree.focus()))
        self.saldi_tree.bind("<<TreeviewOpen>>", lambda e: self._saldi_chiusi.discard(self.saldi_tree.focus()))

    def _apri_gruppi_saldi(self, aperti):
        for item in self.saldi_tree.get_children():
            if self.saldi_tree.get_children(item):
                self.saldi_tree.item(item, open=aperti)
        self._saldi_chiusi = set() if aperti else set(self.saldi_tree.get_children())

    def _on_doppio_clic_saldi(self, event):
        if self.saldi_tree.identify_region(event.x, event.y) in ("cell", "tree"):
            self._apri_partitario(self.saldi_tree.identify_row(event.y))
            return "break"  # niente apertura/chiusura del gruppo con il doppio clic

    # --- Scheda Partitari ---

    def _build_partitario_tab(self):
        barra = ttk.Frame(self.partitario_frame)
        barra.pack(fill=tk.X, padx=px(12), pady=(px(12), 0))
        ttk.Label(barra, text="Conto", style="Secondario.TLabel").pack(side=tk.LEFT, padx=(0, px(8)))
        self._partitario_conto = AutocompleteEntry(barra, values=self._conti_labels, width=34)
        self._partitario_conto.pack(side=tk.LEFT)
        self._partitario_conto._var.trace_add("write", lambda *a: self._on_conto_partitario())

        esporta = ttk.Menubutton(barra, text="Esporta")
        menu = tk.Menu(esporta, tearoff=0)
        for formato, (nome_formato, _ext) in FORMATI.items():
            menu.add_command(label=f"{nome_formato}...", command=lambda f=formato: self._esporta_partitario(f))
        esporta["menu"] = menu
        esporta.pack(side=tk.RIGHT)
        self._partitario_info = ttk.Label(barra, text="", style="Secondario.TLabel")
        self._partitario_info.pack(side=tk.LEFT, padx=(px(12), 0))

        tree_frame = ttk.Frame(self.partitario_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=px(12), pady=(px(10), px(6)))
        cols = ("data", "numero", "causale", "conto", "contropartita", "dare", "avere", "saldo")
        self.partitario_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        for col, titolo, larghezza, allinea, allarga in (
            ("data", "Data", 100, tk.CENTER, False), ("numero", "N.", 50, tk.CENTER, False),
            ("causale", "Causale", 220, tk.W, True), ("conto", "Sottoconto", 170, tk.W, True),
            ("contropartita", "Contropartita", 190, tk.W, True), ("dare", "Dare", 105, tk.E, False),
            ("avere", "Avere", 105, tk.E, False), ("saldo", "Saldo", 115, tk.E, False),
        ):
            self.partitario_tree.heading(col, text=titolo)
            self.partitario_tree.column(col, width=px(larghezza), anchor=allinea, stretch=allarga)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.partitario_tree.yview)
        self.partitario_tree.configure(yscrollcommand=scrollbar.set)
        self.partitario_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.partitario_tree.tag_configure("apertura", foreground=tema.TESTO_SECONDARIO)
        self.partitario_tree.bind("<Double-Button-1>", self._on_doppio_clic_partitario)
        self.partitario_tree.bind("<Return>", lambda e: self._vai_a_registrazione(self.partitario_tree.focus()))

        piede = ttk.Frame(self.partitario_frame)
        piede.pack(side=tk.BOTTOM, fill=tk.X, padx=px(12), pady=(0, px(12)), before=tree_frame)
        self._partitario_totali = ttk.Label(piede, text="", style="Forte.TLabel")
        self._partitario_totali.pack(side=tk.RIGHT)
        ttk.Label(piede, text="Doppio clic su un movimento per aprirlo nel Libro Giornale",
                  style="Secondario.TLabel").pack(side=tk.LEFT)
        self._partitario_conto_id = None

    def _apri_partitario(self, conto_iid):
        """Mostra nella scheda Partitari il conto indicato (iid = id del conto)."""
        if not conto_iid or not conto_iid.isdigit():
            return  # es. la riga "registrato direttamente sul conto"
        conto = self.db.get_conto(int(conto_iid))
        if not conto:
            return
        self._partitario_conto.set_value(f"{conto['codice']} - {conto['nome']}")
        self.notebook.select(self.partitario_frame)

    def _on_conto_partitario(self):
        """Quando nel campo c'è un conto valido, mostra il suo partitario."""
        conto_id = self._conti_map.get(self._partitario_conto.get_value())
        if conto_id and conto_id != self._partitario_conto_id:
            self._partitario_conto_id = conto_id
            self._refresh_partitario()

    def _conti_partitario(self):
        """Il conto scelto e, se è un conto padre, i suoi sottoconti."""
        if not self._partitario_conto_id:
            return None, []
        conto = self.db.get_conto(self._partitario_conto_id)
        if not conto:
            return None, []
        return conto, [conto["id"]] + [s["id"] for s in self.db.get_sottoconti(conto["id"])]

    def _refresh_partitario(self):
        self.partitario_tree.delete(*self.partitario_tree.get_children())
        conto, ids = self._conti_partitario()
        if not conto or not self.esercizio_id:
            self._partitario_info.config(text="Scegli un conto per vederne i movimenti")
            self._partitario_totali.config(text="")
            return
        gruppo = len(ids) > 1
        # La colonna Sottoconto serve solo per un conto padre con sottoconti
        visibili = ["data", "numero", "causale"] + (["conto"] if gruppo else []) + \
                   ["contropartita", "dare", "avere", "saldo"]
        self.partitario_tree.configure(displaycolumns=visibili)

        nomi = {c["id"]: f"{c['codice']} - {c['nome']}" for c in self.db.get_conti() if c["id"] in ids}
        voci = []
        for cid, movimenti in movimenti_partitario(self.db, self.esercizio_id, ids).items():
            voci.extend((reg, cid, contro, dare, avere) for reg, contro, dare, avere in movimenti)
        voci.sort(key=lambda v: (v[0]["data"], v[0]["numero"]))

        segno = SEGNO_SALDO[conto["tipo"]]
        saldo = tot_dare = tot_avere = 0
        for reg, cid, contro, dare, avere in voci:
            saldo += segno * (dare - avere)
            tot_dare += dare
            tot_avere += avere
            self.partitario_tree.insert(
                "", tk.END, iid=f"{reg['id']}-{cid}",
                tags=("apertura",) if reg["descrizione"].startswith(self.db.CAUSALE_APERTURA) else (),
                values=(format_date_display(reg["data"]), reg["numero"], reg["descrizione"], nomi.get(cid, ""),
                        contro, format_importo(dare), format_importo(avere), format_importo(saldo) or "0,00"),
            )
        verso = "Dare - Avere" if segno > 0 else "Avere - Dare"
        sotto = f", {len(ids) - 1} sottoconti" if gruppo else ""
        self._partitario_info.config(
            text=f"{conto['tipo'].capitalize()}{sotto} · {len(voci)} movimenti · saldo {verso}"
        )
        self._partitario_totali.config(
            text=f"Totale Dare: {format_importo(tot_dare) or '0,00'}  |  "
                 f"Totale Avere: {format_importo(tot_avere) or '0,00'}  |  "
                 f"Saldo: {format_importo(saldo) or '0,00'}"
        )

    def _on_doppio_clic_partitario(self, event):
        if self.partitario_tree.identify_region(event.x, event.y) == "cell":
            self._vai_a_registrazione(self.partitario_tree.identify_row(event.y))

    def _vai_a_registrazione(self, iid):
        """Dal partitario al Libro Giornale, sulla registrazione del movimento."""
        if not iid:
            return
        reg_id = iid.split("-")[0]
        self.notebook.select(self.giornale_frame)
        if self.giornale_tree.exists(reg_id):
            self.giornale_tree.selection_set(reg_id)
            self.giornale_tree.focus(reg_id)
            self.giornale_tree.see(reg_id)
            self.giornale_tree.focus_set()

    def _esporta_partitario(self, formato):
        conto, ids = self._conti_partitario()
        if not conto:
            messagebox.showwarning("Attenzione", "Scegli prima un conto nella scheda Partitari.")
            return
        self._on_export("partitari", formato, conto_ids=ids, nome_file=f"partitario_{conto['codice']}")

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
        self._refresh_partitario()
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
            dare_str = self._etichetta_lato(row, "dare")
            avere_str = self._etichetta_lato(row, "avere")
            importo_str = format_importo(row["importo"])
            data_str = format_date_display(row["data"])
            self.giornale_tree.insert(
                "", tk.END,
                iid=str(row["id"]),
                values=(row["numero"], data_str, row["descrizione"],
                        dare_str, avere_str, importo_str),
            )

    @staticmethod
    def _etichetta_lato(reg, lato):
        """Conto in Dare o in Avere; se sono più conti (registrazione composta): "Diversi (codici)"."""
        if reg[f"{lato}_conto_id"] is None:
            return f"Diversi ({reg[f'{lato}_nome']})"
        return f"{reg[f'{lato}_codice']} - {reg[f'{lato}_nome']}"

    def _refresh_saldi(self):
        """
        Saldi in forma di albero: il conto padre mostra il totale del gruppo
        (i suoi movimenti più quelli dei sottoconti); i movimenti registrati
        direttamente sul padre, se ci sono, hanno una riga a parte.
        """
        self.saldi_tree.delete(*self.saldi_tree.get_children())
        if not self.esercizio_id:
            self.totali_label.config(text="")
            return
        rows = self.db.get_saldi(self.esercizio_id)
        figli = {}
        for row in rows:
            if row["padre_id"]:
                figli.setdefault(row["padre_id"], []).append(row)
        ids = {row["id"] for row in rows}

        def valori(tipo, dare, avere):
            return (tipo, format_importo(dare) or "0,00", format_importo(avere) or "0,00",
                    format_importo(dare - avere) or "0,00")

        tot_dare = sum(row["totale_dare"] for row in rows)
        tot_avere = sum(row["totale_avere"] for row in rows)
        for row in rows:
            if row["padre_id"] in ids:
                continue  # sottoconto: inserito sotto il suo padre
            etichetta = f"{row['codice']}   {row['nome']}"
            sotto = figli.get(row["id"], [])
            if not sotto:
                self.saldi_tree.insert("", tk.END, iid=str(row["id"]), text=etichetta,
                                       values=valori(row["tipo"], row["totale_dare"], row["totale_avere"]))
                continue
            dare = row["totale_dare"] + sum(f["totale_dare"] for f in sotto)
            avere = row["totale_avere"] + sum(f["totale_avere"] for f in sotto)
            padre = self.saldi_tree.insert(
                "", tk.END, iid=str(row["id"]), text=etichetta, tags=("gruppo",),
                open=str(row["id"]) not in self._saldi_chiusi, values=valori(row["tipo"], dare, avere),
            )
            if round(row["totale_dare"], 2) or round(row["totale_avere"], 2):
                self.saldi_tree.insert(padre, tk.END, text=f"{row['codice']}   registrato direttamente sul conto",
                                       tags=("diretto",),
                                       values=valori(row["tipo"], row["totale_dare"], row["totale_avere"]))
            for f in sotto:
                self.saldi_tree.insert(padre, tk.END, iid=str(f["id"]), text=f"{f['codice']}   {f['nome']}",
                                       values=valori(f["tipo"], f["totale_dare"], f["totale_avere"]))

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
        elif idx == 2:
            self._refresh_partitario()

    # --- Azioni menu ---

    def _on_nuovo_db(self):
        filepath = filedialog.asksaveasfilename(
            title="Crea un nuovo archivio",
            initialdir=os.path.dirname(self.db.db_path),
            initialfile="contabilino-nuovo.db",
            defaultextension=".db",
            filetypes=[("Archivio di Contabilino", "*.db"), ("Tutti i file", "*.*")],
        )
        if not filepath:
            return
        if os.path.exists(filepath):
            messagebox.showerror(
                "Archivio già esistente",
                "Esiste già un file con questo nome: scegline un altro.\n"
                "(Per usare un archivio esistente scegli File > Apri archivio.)",
            )
            return
        self._switch_db(filepath, new=True)

    def _on_apri_db(self):
        filepath = filedialog.askopenfilename(
            title="Apri un archivio di Contabilino",
            initialdir=os.path.dirname(self.db.db_path),
            filetypes=[("Archivio di Contabilino", "*.db"), ("Tutti i file", "*.*")],
        )
        if not filepath:
            return
        if not info_archivio(filepath):
            messagebox.showerror("File non valido", messaggio_non_valido(filepath))
            return
        self._switch_db(filepath, new=False)

    def _on_mostra_cartella(self):
        """Apre la cartella dell'archivio (utile per il backup: basta copiare il file .db)."""
        cartella = os.path.dirname(os.path.abspath(self.db.db_path))
        try:
            if sys.platform == "win32":
                os.startfile(cartella)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", cartella])
            else:
                subprocess.Popen(["xdg-open", cartella])
        except OSError:
            messagebox.showinfo("Cartella dell'archivio", cartella)

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
        if not reg["semplice"]:
            self._apri_registrazione_composta(reg)
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

    def _apri_registrazione_composta(self, reg=None):
        """Nuova registrazione con più righe, oppure modifica di una esistente (reg)."""
        if not self.esercizio_id:
            messagebox.showwarning("Attenzione", "Selezionare prima un esercizio.")
            return
        esercizio = self.db.get_esercizio(reg["esercizio_id"] if reg else self.esercizio_id)
        if esercizio["data_chiusura"]:
            messagebox.showwarning("Attenzione", "L'esercizio selezionato è chiuso.")
            return
        dlg = RegistrazioneCompostaDialog(
            self.root, self._conti_labels, self._conti_map, esercizio,
            causali=self.db.get_causali_usate(esercizio["id"]), registrazione=reg,
        )
        self.root.wait_window(dlg)
        if not dlg.result:
            return
        data, causale, movimenti = dlg.result
        fuori_ordine_prima = self.db.conta_numeri_fuori_ordine(esercizio["id"])
        try:
            if reg:
                self.db.modifica_registrazione(reg["id"], data, causale, movimenti)
                reg_id = reg["id"]
            else:
                reg_id = self.db.crea_registrazione(esercizio["id"], data, causale, movimenti)
        except (ValueError, sqlite3.Error) as e:
            messagebox.showerror("Errore", str(e))
            return
        self._refresh_giornale()
        self._refresh_causali_cache()
        self.giornale_tree.selection_set(str(reg_id))
        self.giornale_tree.see(str(reg_id))
        numero = self.db.get_registrazione_compatta(reg_id)["numero"]
        self.status_var.set(f"Registrazione composta n. {numero} {'modificata' if reg else 'salvata'}: {causale}")
        if self.db.conta_numeri_fuori_ordine(esercizio["id"]) > fuori_ordine_prima:
            self._chiedi_rinumerazione(
                f"La registrazione n. {numero} ha una data precedente a registrazioni\n"
                "con un numero più basso.\n\n", seleziona=reg_id,
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

    def _on_export(self, tipo, formato, conto_ids=None, nome_file=None):
        """Export di un report. Con conto_ids (es. dalla scheda Partitari) non chiede quali conti."""
        if not self.esercizio_id:
            messagebox.showwarning("Attenzione", "Selezionare prima un esercizio.")
            return

        tipo_label, nome_base = self._EXPORT[tipo]
        nome_formato, ext = FORMATI[formato]
        esercizio = self.db.get_esercizio(self.esercizio_id)

        # Saldi, costi e ricavi, partitari: tutti i conti oppure solo quelli scelti
        opzioni = {}
        if conto_ids is not None:
            opzioni["conto_ids"] = conto_ids
            nome_base = nome_file or nome_base
        elif tipo != "giornale":
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
        if conto_ids is None and opzioni and self._selezioni_export.get(tipo) == "economici":
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
