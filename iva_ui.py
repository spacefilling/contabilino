"""
Contabilino - Finestre del modulo IVA
Registrazione di fatture, note di credito e corrispettivi, consultazione e
stampa dei registri IVA, liquidazione periodica, impostazioni del modulo.
"""

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from dateutils import data_in_periodo, format_display, periodo_label
from iva import (ACQUISTI, CORRISPETTIVI, DOC_CORRISPETTIVI, FATTURA, MESI, NOTA_CREDITO, VENDITE,
                 AUTOFATTURA, ModuloIva, r2)
from tema import px
from widgets import AmountEntry, AutocompleteEntry, SmartDateEntry, format_importo


def _centra(finestra, parent):
    finestra.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - finestra.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - finestra.winfo_height()) // 4
    finestra.geometry(f"+{max(0, x)}+{max(0, y)}")


def _etichetta_conto(c):
    return f"{c['codice']} - {c['nome']}"


TITOLI = {
    (ACQUISTI, FATTURA): "Fattura di acquisto",
    (ACQUISTI, NOTA_CREDITO): "Nota di credito ricevuta",
    (VENDITE, FATTURA): "Fattura di vendita",
    (VENDITE, NOTA_CREDITO): "Nota di credito emessa",
    (CORRISPETTIVI, DOC_CORRISPETTIVI): "Corrispettivi",
}


class DocumentoIvaDialog(tk.Toplevel):
    """
    Registrazione di un documento IVA: fattura o nota di credito (acquisti o
    vendite) oppure corrispettivi. Genera la scrittura contabile e il documento
    nel registro. Con registrazione_id modifica un documento già registrato.
    Alla chiusura: result = id della registrazione (None se annullato).
    """

    def __init__(self, parent, db, esercizio, tipo_registro, tipo_documento, registrazione_id=None):
        super().__init__(parent)
        self.db = db
        self.modulo = ModuloIva(db)
        self.esercizio = esercizio
        self.tipo_registro = tipo_registro
        self.tipo_documento = tipo_documento
        self.registrazione_id = registrazione_id
        self.result = None
        self.corrispettivi = tipo_registro == CORRISPETTIVI
        self.acquisti = tipo_registro == ACQUISTI
        self._righe = []

        conti = db.get_conti()
        self._conti_map = {_etichetta_conto(c): c["id"] for c in conti}
        self._conti_labels = list(self._conti_map)
        self._aliquote = {f"{a['codice']} - {a['descrizione']}": a for a in self.modulo.get_aliquote()}
        self._registri = {f"{r['codice']} - {r['descrizione']}": r for r in self.modulo.get_registri(tipo_registro)}

        titolo = TITOLI.get((tipo_registro, tipo_documento), "Documento IVA")
        self.title(("Modifica: " if registrazione_id else "") + titolo)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._build_ui(titolo)
        if registrazione_id:
            self._carica(registrazione_id)
        else:
            self._aggiungi_riga()
        self._aggiorna()
        self.bind("<Escape>", lambda e: self.destroy())
        _centra(self, parent)

    # --- Interfaccia ---

    def _build_ui(self, titolo):
        f = ttk.Frame(self, padding=px(16))
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=titolo, style="Sottotitolo.TLabel").pack(anchor=tk.W)

        testa = ttk.Frame(f)
        testa.pack(fill=tk.X, pady=(px(10), 0))
        etichette = ["Registro", "Data registrazione"]
        if not self.corrispettivi:
            etichette += ["Data documento", "N. documento"]
        for col, testo in enumerate(etichette):
            ttk.Label(testa, text=testo, style="Secondario.TLabel").grid(row=0, column=col, sticky=tk.W, padx=px(3))
        self._registro_cb = ttk.Combobox(testa, values=list(self._registri), state="readonly", width=28)
        self._registro_cb.grid(row=1, column=0, padx=px(3), sticky=tk.W)
        if self._registri:
            self._registro_cb.set(next(iter(self._registri)))
        self._data_reg = SmartDateEntry(testa, width=12)
        self._data_reg.grid(row=1, column=1, padx=px(3), sticky=tk.W)
        self._data_reg.set_iso_date(self._data_proposta())
        if not self.corrispettivi:
            self._data_doc = SmartDateEntry(testa, width=12)
            self._data_doc.grid(row=1, column=2, padx=px(3), sticky=tk.W)
            self._numero = ttk.Entry(testa, width=14)
            self._numero.grid(row=1, column=3, padx=px(3), sticky=tk.W)

        seconda = ttk.Frame(f)
        seconda.pack(fill=tk.X, pady=(px(8), 0))
        controparte = ("Conto di incasso (cassa, banca...)" if self.corrispettivi
                       else "Fornitore" if self.acquisti else "Cliente")
        ttk.Label(seconda, text=controparte, style="Secondario.TLabel").grid(row=0, column=0, sticky=tk.W, padx=px(3))
        ttk.Label(seconda, text="Causale (facoltativa)", style="Secondario.TLabel").grid(row=0, column=1, sticky=tk.W, padx=px(3))
        self._controparte = AutocompleteEntry(seconda, values=self._conti_labels, width=36)
        self._controparte.grid(row=1, column=0, padx=px(3), sticky=tk.W)
        self._causale = ttk.Entry(seconda, width=40)
        self._causale.grid(row=1, column=1, padx=px(3), sticky=tk.W + tk.E)
        if self.corrispettivi:
            incasso = self.modulo.conto_ruolo("incasso_corrispettivi")
            conto = self.db.get_conto(incasso) if incasso else next(
                (c for c in self.db.get_conti() if c["nome"].lower().startswith("cassa")), None)
            if conto:
                self._controparte.set_value(_etichetta_conto(conto))

        self._rc_var = tk.BooleanVar(value=False)
        if self.acquisti:
            ttk.Checkbutton(
                f, variable=self._rc_var, command=self._aggiorna,
                text="Reverse charge (inversione contabile: l'IVA va anche nel registro vendite)",
            ).pack(anchor=tk.W, pady=(px(8), 0))

        self._griglia = ttk.Frame(f)
        self._griglia.pack(fill=tk.X, pady=(px(10), 0))
        intestazioni = ["Conto di ricavo" if not self.acquisti else "Conto di costo",
                        "Totale lordo" if self.corrispettivi else "Imponibile", "Aliquota", "Imposta"]
        if self.acquisti:
            intestazioni.append("% detraibile")
        for col, testo in enumerate(intestazioni):
            ttk.Label(self._griglia, text=testo, style="Secondario.TLabel").grid(row=0, column=col, sticky=tk.W, padx=px(3))

        comandi = ttk.Frame(f)
        comandi.pack(fill=tk.X, pady=(px(6), 0))
        ttk.Button(comandi, text="+ Aggiungi riga", command=lambda: self._aggiungi_riga(focus=True)).pack(side=tk.LEFT)
        self._totali = ttk.Label(comandi, style="Forte.TLabel")
        self._totali.pack(side=tk.RIGHT)

        ttk.Label(f, text="Scrittura contabile", style="Secondario.TLabel").pack(anchor=tk.W, pady=(px(10), 0))
        self._anteprima = ttk.Label(f, style="Nota.TLabel", justify=tk.LEFT, font=("Courier", 10))
        self._anteprima.pack(anchor=tk.W)

        btn = ttk.Frame(f)
        btn.pack(pady=(px(14), 0))
        ttk.Button(btn, text="Registra", style="Accent.TButton", command=self._on_registra).pack(side=tk.LEFT, padx=px(4))
        ttk.Button(btn, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=px(4))

    def _data_proposta(self):
        oggi = date.today().isoformat()
        es = self.esercizio
        return oggi if data_in_periodo(oggi, es["data_inizio"], es["data_fine"]) else es["data_fine"]

    def _aggiungi_riga(self, conto="", importo=0.0, aliquota=None, imposta=None, detraibile=100, focus=False):
        r = len(self._righe) + 1
        riga = {"manuale": imposta is not None}
        riga["conto"] = AutocompleteEntry(self._griglia, values=self._conti_labels, width=34)
        riga["importo"] = AmountEntry(self._griglia, width=12)
        riga["aliquota"] = ttk.Combobox(self._griglia, values=list(self._aliquote), state="readonly", width=24)
        riga["imposta"] = AmountEntry(self._griglia, width=11)
        widget = [riga["conto"], riga["importo"], riga["aliquota"], riga["imposta"]]
        if self.acquisti:
            riga["detraibile"] = ttk.Spinbox(self._griglia, from_=0, to=100, increment=10, width=5,
                                             command=self._aggiorna)
            riga["detraibile"].set(int(detraibile))
            riga["detraibile"].bind("<KeyRelease>", lambda e: self._aggiorna())
            widget.append(riga["detraibile"])
        riga["togli"] = ttk.Button(self._griglia, text="✕", width=3, command=lambda: self._togli_riga(riga))
        widget.append(riga["togli"])
        for col, w in enumerate(widget):
            w.grid(row=r, column=col, padx=px(3), pady=px(2), sticky=tk.W + tk.E)
        if self.corrispettivi:
            riga["imposta"].configure(state="disabled")  # calcolata con lo scorporo
        if conto:
            riga["conto"].set_value(conto)
        if importo:
            riga["importo"].set_amount(importo)
        riga["aliquota"].set(aliquota or next(iter(self._aliquote), ""))
        if imposta is not None:
            riga["imposta"].set_amount(imposta)
        riga["importo"].bind("<KeyRelease>", lambda e: self._ricalcola(riga), add="+")
        riga["importo"].bind("<<Paste>>", lambda e: self.after(1, lambda: self._ricalcola(riga)), add="+")
        riga["aliquota"].bind("<<ComboboxSelected>>", lambda e: self._ricalcola(riga, forza=True))
        riga["imposta"].bind("<KeyRelease>", lambda e: (riga.update(manuale=True), self._aggiorna()), add="+")
        self._righe.append(riga)
        if focus:
            riga["conto"].focus_set()
        return riga

    def _togli_riga(self, riga):
        for k, w in riga.items():
            if k != "manuale":
                w.destroy()
        self._righe.remove(riga)
        for r, rr in enumerate(self._righe, 1):
            col = 0
            for k in ("conto", "importo", "aliquota", "imposta", "detraibile", "togli"):
                if k in rr:
                    rr[k].grid_configure(row=r, column=col)
                    col += 1
        self._aggiorna()

    def _ricalcola(self, riga, forza=False):
        """Imposta calcolata dall'imponibile (se l'utente non l'ha cambiata a mano)."""
        aliquota = self._aliquote.get(riga["aliquota"].get())
        if aliquota and (forza or not riga["manuale"]) and not self.corrispettivi:
            riga["manuale"] = False
            riga["imposta"].set_amount(r2(riga["importo"].get_amount() * aliquota["percentuale"] / 100))
        self._aggiorna()

    def _righe_documento(self, controlla=False):
        """Righe come le vuole ModuloIva; con controlla=True solleva ValueError sugli errori."""
        righe = []
        for n, r in enumerate(self._righe, 1):
            conto, importo = r["conto"].get_value(), r["importo"].get_amount()
            if not conto and not importo:
                continue
            if conto not in self._conti_map:
                if controlla:
                    raise ValueError(f"Riga {n}: scegliere il conto dall'elenco.")
                continue
            aliquota = self._aliquote.get(r["aliquota"].get())
            if not aliquota:
                if controlla:
                    raise ValueError(f"Riga {n}: scegliere l'aliquota.")
                continue
            if self.corrispettivi:
                imponibile, imposta = self.modulo.scorpora(importo, aliquota["percentuale"])
            else:
                imponibile, imposta = importo, r["imposta"].get_amount()
            try:
                detraibile = float(r["detraibile"].get()) if self.acquisti else 100.0
            except ValueError:
                detraibile = 100.0
            if controlla and not 0 <= detraibile <= 100:
                raise ValueError(f"Riga {n}: la percentuale detraibile va da 0 a 100.")
            righe.append({"conto_id": self._conti_map[conto], "imponibile": imponibile, "imposta": imposta,
                          "aliquota_id": aliquota["id"], "detraibile": detraibile})
        if controlla and not righe:
            raise ValueError("Inserire almeno una riga con conto e importo.")
        return righe

    def _aggiorna(self):
        righe = self._righe_documento()
        imponibile = r2(sum(r["imponibile"] for r in righe))
        imposta = r2(sum(r["imposta"] for r in righe))
        for r in self._righe:  # nei corrispettivi l'imposta si mostra calcolata
            if self.corrispettivi:
                aliquota = self._aliquote.get(r["aliquota"].get())
                if aliquota:
                    r["imposta"].configure(state="normal")
                    r["imposta"].set_amount(self.modulo.scorpora(r["importo"].get_amount(), aliquota["percentuale"])[1])
                    r["imposta"].configure(state="disabled")
        self._totali.config(text=f"Imponibile {format_importo(imponibile) or '0,00'}   ·   "
                                 f"Imposta {format_importo(imposta) or '0,00'}   ·   "
                                 f"Totale {format_importo(imponibile + imposta) or '0,00'}")
        controparte = self._conti_map.get(self._controparte.get_value())
        if not righe or not controparte:
            self._anteprima.config(text="(scegli la controparte e inserisci le righe)")
            return
        try:
            movimenti = self.modulo.movimenti_documento(self.tipo_registro, self.tipo_documento, controparte,
                                                        righe, self._rc_var.get())
        except ValueError as e:
            self._anteprima.config(text=str(e))
            return
        nomi = {c["id"]: _etichetta_conto(c) for c in self.db.get_conti()}
        testo = []
        for conto_id, dare, avere in movimenti:
            nome = nomi.get(conto_id, "?")[:40]
            testo.append(f"{nome:<42}{(format_importo(dare) if dare else ''):>12}{(format_importo(avere) if avere else ''):>12}")
        self._anteprima.config(text=f"{'Conto':<42}{'Dare':>12}{'Avere':>12}\n" + "\n".join(testo))

    # --- Caricamento e registrazione ---

    def _carica(self, registrazione_id):
        documenti = [d for d in self.modulo.documenti_della_registrazione(registrazione_id)
                     if d["tipo_documento"] != AUTOFATTURA]
        if not documenti:
            return
        doc = documenti[0]
        reg = self.db.get_registrazione_compatta(registrazione_id)
        for label, r in self._registri.items():
            if r["id"] == doc["registro_id"]:
                self._registro_cb.set(label)
        self._data_reg.set_iso_date(doc["data_registrazione"])
        if not self.corrispettivi:
            if doc["data_documento"]:
                self._data_doc.set_iso_date(doc["data_documento"])
            self._numero.insert(0, doc["numero_documento"] or "")
        conto = self.db.get_conto(doc["controparte_id"]) if doc["controparte_id"] else None
        if conto:
            self._controparte.set_value(_etichetta_conto(conto))
        self._causale.insert(0, reg["descrizione"] if reg else "")
        self._rc_var.set(bool(doc["reverse_charge"]))
        aliquote_per_id = {a["id"]: label for label, a in self._aliquote.items()}
        for r in self.modulo.righe_documento(doc["id"]):
            conto_riga = self.db.get_conto(r["conto_id"]) if r["conto_id"] else None
            self._aggiungi_riga(
                conto=_etichetta_conto(conto_riga) if conto_riga else "",
                importo=r2(r["imponibile"] + r["imposta"]) if self.corrispettivi else r["imponibile"],
                aliquota=aliquote_per_id.get(r["aliquota_id"]),
                imposta=None if self.corrispettivi else r["imposta"],
                detraibile=r["detraibile"],
            )

    def _on_registra(self):
        self._data_reg._format()
        data = self._data_reg.get_iso_date()
        es = self.esercizio
        try:
            registro = self._registri.get(self._registro_cb.get())
            if not registro:
                raise ValueError("Scegliere il registro IVA (vedi IVA > Impostazioni IVA).")
            if not data:
                raise ValueError("Data di registrazione non valida (GG/MM/AAAA).")
            if not data_in_periodo(data, es["data_inizio"], es["data_fine"]):
                raise ValueError(f"La data non rientra nell'esercizio {es['descrizione']} "
                                 f"({periodo_label(es['data_inizio'], es['data_fine'])}).")
            controparte = self._conti_map.get(self._controparte.get_value())
            if not controparte:
                raise ValueError("Scegliere dall'elenco " + ("il conto di incasso." if self.corrispettivi
                                                            else "il fornitore." if self.acquisti else "il cliente."))
            righe = self._righe_documento(controlla=True)
            data_doc = numero = None
            if not self.corrispettivi:
                self._data_doc._format()
                data_doc = self._data_doc.get_iso_date() or None
                numero = self._numero.get().strip() or None
        except ValueError as e:
            messagebox.showerror("Errore", str(e), parent=self)
            return

        # Periodo già liquidato: avvisa (i totali della liquidazione salvata cambierebbero)
        anno, mese = int(data[:4]), int(data[5:7])
        periodicita = self.modulo.periodicita
        periodo = mese if periodicita == "M" else (mese - 1) // 3 + 1
        if self.modulo.get_liquidazione(anno, periodicita, periodo) and not messagebox.askyesno(
                "Periodo già liquidato",
                f"La liquidazione IVA di {self.modulo.nome_periodo(anno, periodicita, periodo)} è già stata "
                "salvata.\nRegistrando questo documento andrà ricalcolata. Continuare?", parent=self):
            return

        causale = self._causale.get().strip()
        if not causale:
            nome = self._controparte.get_value().split(" - ", 1)[-1]
            causale = (f"Corrispettivi del {format_display(data)}" if self.corrispettivi else
                       f"{TITOLI[(self.tipo_registro, self.tipo_documento)]}"
                       f"{' n. ' + numero if numero else ''} - {nome}")
        try:
            self.result = self.modulo.registra_documento(
                es["id"], registro["id"], data, causale, controparte, righe,
                tipo_documento=self.tipo_documento, data_documento=data_doc, numero_documento=numero,
                reverse_charge=self._rc_var.get() and self.acquisti, registrazione_id=self.registrazione_id,
            )
        except ValueError as e:
            messagebox.showerror("Errore", str(e), parent=self)
            return
        self.destroy()


def tipo_documento_della_registrazione(db, registrazione_id):
    """(tipo registro, tipo documento) del documento IVA di una registrazione, oppure None."""
    for d in ModuloIva(db).documenti_della_registrazione(registrazione_id):
        if d["tipo_documento"] != AUTOFATTURA:
            return d["registro_tipo"], d["tipo_documento"]
    return None


# --- Scelta del periodo (registri e liquidazione) ---

class _ScegliPeriodo(ttk.Frame):
    """Anno e periodo: mese, trimestre oppure anno intero."""

    def __init__(self, master, tipi=("M", "T", "A"), tipo="M", on_change=None):
        super().__init__(master)
        self._on_change = on_change or (lambda: None)
        oggi = date.today()
        self.tipo_var = tk.StringVar(value=tipo)
        nomi = {"M": "Mese", "T": "Trimestre", "A": "Anno"}
        for t in tipi:
            ttk.Radiobutton(self, text=nomi[t], value=t, variable=self.tipo_var,
                            command=self._aggiorna).pack(side=tk.LEFT, padx=(0, px(8)))
        self.anno = ttk.Spinbox(self, from_=2000, to=2100, width=6, command=self._on_change)
        self.anno.set(oggi.year)
        self.anno.bind("<KeyRelease>", lambda e: self._on_change())
        self.anno.pack(side=tk.LEFT, padx=(px(8), px(4)))
        self.periodo = ttk.Combobox(self, state="readonly", width=16)
        self.periodo.pack(side=tk.LEFT)
        self.periodo.bind("<<ComboboxSelected>>", lambda e: self._on_change())
        self._aggiorna(iniziale=oggi)

    def _aggiorna(self, iniziale=None):
        tipo = self.tipo_var.get()
        if tipo == "M":
            self.periodo.configure(values=[m.capitalize() for m in MESI], state="readonly")
            self.periodo.current((iniziale or date.today()).month - 1)
        elif tipo == "T":
            self.periodo.configure(values=[f"{n}° trimestre" for n in range(1, 5)], state="readonly")
            self.periodo.current(((iniziale or date.today()).month - 1) // 3)
        else:
            self.periodo.configure(values=["Anno intero"])
            self.periodo.current(0)
            self.periodo.configure(state="disabled")
        self._on_change()

    def valori(self):
        """(anno, tipo, numero del periodo)."""
        try:
            anno = int(self.anno.get())
        except ValueError:
            anno = date.today().year
        return anno, self.tipo_var.get(), self.periodo.current() + 1

    def date(self):
        anno, tipo, n = self.valori()
        if tipo == "A":
            return f"{anno}-01-01", f"{anno}-12-31", f"Anno {anno}"
        return (*ModuloIva.periodo_date(anno, tipo, n), ModuloIva.nome_periodo(anno, tipo, n).capitalize())


# --- Registri IVA ---

class RegistriIvaDialog(tk.Toplevel):
    """Consultazione e stampa di un registro IVA per mese, trimestre o anno."""

    def __init__(self, parent, db, esporta):
        super().__init__(parent)
        self.db = db
        self.modulo = ModuloIva(db)
        self._esporta = esporta  # funzione(report, nome_file, formato) della finestra principale
        self.title("Registri IVA")
        self.transient(parent)
        self.grab_set()
        self._registri = {f"{r['codice']} - {r['descrizione']}": r for r in self.modulo.get_registri(solo_attivi=False)}

        f = ttk.Frame(self, padding=px(16))
        f.pack(fill=tk.BOTH, expand=True)
        barra = ttk.Frame(f)
        barra.pack(fill=tk.X)
        ttk.Label(barra, text="Registro", style="Secondario.TLabel").pack(side=tk.LEFT, padx=(0, px(6)))
        self._registro = ttk.Combobox(barra, values=list(self._registri), state="readonly", width=32)
        self._registro.pack(side=tk.LEFT)
        if self._registri:
            self._registro.current(0)
        self._registro.bind("<<ComboboxSelected>>", lambda e: self._aggiorna())
        self._periodo = _ScegliPeriodo(f, tipo=self.modulo.periodicita, on_change=self._aggiorna)
        self._periodo.pack(fill=tk.X, pady=(px(8), 0))

        cols = ("prot", "data", "doc", "controparte", "aliquota", "imponibile", "imposta")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", height=14)
        for col, titolo, w, a in (("prot", "Prot.", 50, tk.CENTER), ("data", "Data reg.", 95, tk.CENTER),
                                  ("doc", "N. doc.", 90, tk.W), ("controparte", "Controparte", 240, tk.W),
                                  ("aliquota", "Aliquota", 70, tk.CENTER), ("imponibile", "Imponibile", 110, tk.E),
                                  ("imposta", "Imposta", 100, tk.E)):
            self.tree.heading(col, text=titolo)
            self.tree.column(col, width=px(w), anchor=a, stretch=col == "controparte")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(px(10), 0))
        self._totali = ttk.Label(f, style="Forte.TLabel")
        self._totali.pack(anchor=tk.E, pady=(px(6), 0))

        btn = ttk.Frame(f)
        btn.pack(fill=tk.X, pady=(px(10), 0))
        for formato, testo in (("pdf", "Stampa PDF..."), ("xlsx", "Excel..."), ("csv", "CSV...")):
            ttk.Button(btn, text=testo, style="Accent.TButton" if formato == "pdf" else "TButton",
                       command=lambda fo=formato: self._on_esporta(fo)).pack(side=tk.LEFT, padx=(0, px(6)))
        ttk.Button(btn, text="Chiudi", command=self.destroy).pack(side=tk.RIGHT)
        self.bind("<Escape>", lambda e: self.destroy())
        self._aggiorna()
        _centra(self, parent)

    def _aggiorna(self):
        if not hasattr(self, "tree"):
            return
        self.tree.delete(*self.tree.get_children())
        registro = self._registri.get(self._registro.get())
        if not registro:
            return
        dal, al, _nome = self._periodo.date()
        documento = None
        for r in self.modulo.righe_registro(registro["id"], dal, al):
            s = self.modulo.segno_documento(r["tipo_documento"])
            nuovo = r["documento_id"] != documento
            documento = r["documento_id"]
            self.tree.insert("", tk.END, values=(
                r["protocollo"] if nuovo else "", format_display(r["data_registrazione"]) if nuovo else "",
                (r["numero_documento"] or "") if nuovo else "",
                f"{r['controparte_codice']} - {r['controparte_nome']}" if nuovo and r["controparte_codice"] else "",
                r["aliquota_codice"], format_importo(s * r["imponibile"]) or "0,00",
                format_importo(s * r["imposta"]) or "0,00"))
        totali = self.modulo.totali_registro(registro["id"], dal, al)
        self._totali.config(text=f"Imponibile {format_importo(sum(t['imponibile'] for t in totali.values())) or '0,00'}"
                                 f"   ·   Imposta {format_importo(sum(t['imposta'] for t in totali.values())) or '0,00'}")

    def _on_esporta(self, formato):
        from export import report_registro_iva
        registro = self._registri.get(self._registro.get())
        if not registro:
            return
        dal, al, nome = self._periodo.date()
        report = report_registro_iva(self.db, registro["id"], dal, al, nome)
        self._esporta(report, f"registro_iva_{registro['codice']}_{dal[:7] if dal[5:7] == al[5:7] else dal[:4] + '_' + dal[5:7] + '-' + al[5:7]}", formato)


# --- Liquidazione ---

class LiquidazioneDialog(tk.Toplevel):
    """Liquidazione IVA del periodo: calcolo, salvataggio, giroconto e stampa."""

    def __init__(self, parent, db, esporta, aggiorna_giornale):
        super().__init__(parent)
        self.db = db
        self.modulo = ModuloIva(db)
        self._esporta = esporta
        self._aggiorna_giornale = aggiorna_giornale
        self.liq = None
        self.title("Liquidazione IVA")
        self.transient(parent)
        self.grab_set()

        f = ttk.Frame(self, padding=px(16))
        f.pack(fill=tk.BOTH, expand=True)
        per = "mensile" if self.modulo.periodicita == "M" else "trimestrale"
        ttk.Label(f, text=f"Liquidazione {per}", style="Sottotitolo.TLabel").pack(anchor=tk.W)
        ttk.Label(f, text="(la periodicità si cambia in IVA > Impostazioni IVA)", style="Secondario.TLabel").pack(anchor=tk.W)
        self._periodo = _ScegliPeriodo(f, tipi=(self.modulo.periodicita,), tipo=self.modulo.periodicita,
                                       on_change=self._calcola)
        self._periodo.pack(fill=tk.X, pady=(px(8), 0))

        campi = ttk.Frame(f)
        campi.pack(fill=tk.X, pady=(px(8), 0))
        ttk.Label(campi, text="Credito anno precedente (solo 1° periodo)", style="Secondario.TLabel").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(campi, text="Acconto versato (dicembre / 4° trimestre)", style="Secondario.TLabel").grid(row=0, column=1, sticky=tk.W, padx=(px(12), 0))
        self._credito = AmountEntry(campi, width=14)
        self._credito.grid(row=1, column=0, sticky=tk.W)
        self._acconto = AmountEntry(campi, width=14)
        self._acconto.grid(row=1, column=1, sticky=tk.W, padx=(px(12), 0))
        for w in (self._credito, self._acconto):
            w.bind("<KeyRelease>", lambda e: self._calcola(), add="+")

        self.tree = ttk.Treeview(f, columns=("importo",), show="tree headings", height=12)
        self.tree.heading("#0", text="Voce", anchor=tk.W)
        self.tree.heading("importo", text="Importo")
        self.tree.column("#0", width=px(380))
        self.tree.column("importo", width=px(130), anchor=tk.E, stretch=False)
        self.tree.tag_configure("totale", font="Contabilino.Forte")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(px(10), 0))
        self._stato = ttk.Label(f, style="Secondario.TLabel")
        self._stato.pack(anchor=tk.W, pady=(px(4), 0))

        btn = ttk.Frame(f)
        btn.pack(fill=tk.X, pady=(px(10), 0))
        ttk.Button(btn, text="Salva liquidazione", style="Accent.TButton", command=self._on_salva).pack(side=tk.LEFT)
        ttk.Button(btn, text="Registra giroconto...", command=self._on_giroconto).pack(side=tk.LEFT, padx=px(6))
        ttk.Button(btn, text="Stampa PDF...", command=lambda: self._on_esporta("pdf")).pack(side=tk.LEFT)
        ttk.Button(btn, text="Excel...", command=lambda: self._on_esporta("xlsx")).pack(side=tk.LEFT, padx=px(6))
        ttk.Button(btn, text="Chiudi", command=self.destroy).pack(side=tk.RIGHT)
        self.bind("<Escape>", lambda e: self.destroy())
        self._calcola()
        _centra(self, parent)

    def _calcola(self):
        if not hasattr(self, "tree"):
            return
        anno, tipo, periodo = self._periodo.valori()
        credito = self._credito.get_amount() if periodo == 1 else None
        self.liq = liq = self.modulo.calcola_liquidazione(anno, periodo, tipo, credito_precedente=credito,
                                                          acconto=self._acconto.get_amount())
        self.tree.delete(*self.tree.get_children())
        deb = self.tree.insert("", tk.END, text="IVA a debito", values=(format_importo(liq["iva_debito"]) or "0,00",),
                               open=True, tags=("totale",))
        cre = self.tree.insert("", tk.END, text="IVA detraibile", values=(format_importo(liq["iva_credito"]) or "0,00",),
                               open=True, tags=("totale",))
        for d in liq["dettaglio"]:
            nome = f"{d['registro']['codice']} - {d['registro']['descrizione']}"
            if d["debito"]:
                self.tree.insert(deb, tk.END, text=nome, values=(format_importo(d["debito"]),))
            if d["credito"]:
                self.tree.insert(cre, tk.END, text=nome, values=(format_importo(d["credito"]),))
        for testo, valore in (("Credito del periodo precedente", -liq["credito_precedente"]),
                              ("Debito del periodo precedente (sotto 25,82 €)", liq["debito_precedente"]),
                              ("Interessi 1% (trimestrale)", liq["interessi"]), ("Acconto versato", -liq["acconto"])):
            if valore:
                self.tree.insert("", tk.END, text=testo, values=(format_importo(valore),))
        r = liq["risultato"]
        esito = ("Credito da riportare" if r < 0 else "IVA da versare" if liq["da_versare"]
                 else "Debito sotto 25,82 €: si riporta")
        self.tree.insert("", tk.END, text=esito, values=(format_importo(abs(r)) or "0,00",), tags=("totale",))
        salvata = self.modulo.get_liquidazione(anno, tipo, periodo)
        self._stato.config(text="Liquidazione già salvata" + (" e registrata nel giornale" if salvata and salvata["registrazione_id"] else "")
                           if salvata else "Liquidazione non ancora salvata")

    def _on_salva(self):
        self.modulo.salva_liquidazione(self.liq)
        self._calcola()

    def _on_giroconto(self):
        liq = self.liq
        esercizio = self.db.get_esercizio_per_data(liq["al"])
        if not esercizio or esercizio["data_chiusura"]:
            messagebox.showerror("Errore", f"Nessun esercizio aperto comprende il {format_display(liq['al'])}.", parent=self)
            return
        salvata = self.modulo.get_liquidazione(liq["anno"], liq["periodicita"], liq["periodo"])
        if salvata and salvata["registrazione_id"] and self.db.get_registrazione_compatta(salvata["registrazione_id"]):
            messagebox.showinfo("Giroconto", "Il giroconto di questo periodo è già registrato nel giornale.", parent=self)
            return
        if not messagebox.askyesno(
                "Registra giroconto",
                f"Registrare al {format_display(liq['al'])} il giroconto di liquidazione?\n\n"
                "IVA su vendite e IVA su acquisti si chiudono su Erario c/IVA.\n"
                "Il versamento F24 si registra poi a parte (Erario c/IVA a Banca).", parent=self):
            return
        try:
            self.modulo.salva_liquidazione(liq)
            self.modulo.registra_giroconto(liq, esercizio["id"])
        except ValueError as e:
            messagebox.showerror("Errore", str(e), parent=self)
            return
        self._aggiorna_giornale()
        self._calcola()

    def _on_esporta(self, formato):
        from export import report_liquidazione_iva
        liq = self.liq
        self._esporta(report_liquidazione_iva(self.db, liq),
                      f"liquidazione_iva_{liq['anno']}_{liq['periodicita']}{liq['periodo']:02d}", formato)


# --- Impostazioni del modulo ---

class ImpostazioniIvaDialog(tk.Toplevel):
    """Periodicità, conti IVA, registri sezionali, aliquote e dati dell'azienda."""

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.modulo = ModuloIva(db)
        self.title("Impostazioni IVA")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        f = ttk.Frame(self, padding=px(16))
        f.pack(fill=tk.BOTH, expand=True)
        schede = ttk.Notebook(f)
        schede.pack(fill=tk.BOTH, expand=True)
        self._scheda_generale(schede)
        self._scheda_registri(schede)
        self._scheda_aliquote(schede)
        self._scheda_azienda(schede)
        btn = ttk.Frame(f)
        btn.pack(fill=tk.X, pady=(px(12), 0))
        ttk.Button(btn, text="Salva", style="Accent.TButton", command=self._on_salva).pack(side=tk.RIGHT)
        ttk.Button(btn, text="Annulla", command=self.destroy).pack(side=tk.RIGHT, padx=px(6))
        self.bind("<Escape>", lambda e: self.destroy())
        _centra(self, parent)

    def _scheda_generale(self, schede):
        s = ttk.Frame(schede, padding=px(12))
        schede.add(s, text="Generale")
        ttk.Label(s, text="Liquidazione", style="Forte.TLabel").grid(row=0, column=0, sticky=tk.W)
        self._periodicita = tk.StringVar(value=self.modulo.periodicita)
        ttk.Radiobutton(s, text="Mensile", value="M", variable=self._periodicita).grid(row=1, column=0, sticky=tk.W)
        ttk.Radiobutton(s, text="Trimestrale (con interessi dell'1%)", value="T",
                        variable=self._periodicita).grid(row=2, column=0, sticky=tk.W)
        conti = self.db.get_conti()
        etichette = [""] + [_etichetta_conto(c) for c in conti]
        self._map = {_etichetta_conto(c): c["id"] for c in conti}
        self._ruoli = {}
        for i, (ruolo, testo) in enumerate((("acquisti", "Conto IVA su acquisti (credito)"),
                                            ("vendite", "Conto IVA su vendite (debito)"),
                                            ("erario", "Conto Erario c/IVA (liquidazione)"),
                                            ("incasso_corrispettivi", "Conto di incasso proposto per i corrispettivi")), 3):
            ttk.Label(s, text=testo, style="Secondario.TLabel").grid(row=2 * i - 2, column=0, sticky=tk.W, pady=(px(8), 0))
            cb = ttk.Combobox(s, values=etichette, state="readonly", width=44)
            cb.grid(row=2 * i - 1, column=0, sticky=tk.W)
            attuale = self.modulo.conto_ruolo(ruolo)
            conto = self.db.get_conto(attuale) if attuale else None
            cb.set(_etichetta_conto(conto) if conto else "")
            self._ruoli[ruolo] = cb
        ttk.Label(s, text="Registro vendite per il reverse charge", style="Secondario.TLabel").grid(row=12, column=0, sticky=tk.W, pady=(px(8), 0))
        self._reg_rc = ttk.Combobox(s, values=[f"{r['codice']} - {r['descrizione']}" for r in self.modulo.get_registri(VENDITE)],
                                    state="readonly", width=44)
        self._reg_rc.grid(row=13, column=0, sticky=tk.W)
        rc = self.modulo.get_registro(self.modulo.registro_reverse_charge()) if self.modulo.registro_reverse_charge() else None
        if rc:
            self._reg_rc.set(f"{rc['codice']} - {rc['descrizione']}")

    def _scheda_registri(self, schede):
        s = ttk.Frame(schede, padding=px(12))
        schede.add(s, text="Registri")
        ttk.Label(s, text="Registri sezionali: uno o più per tipo (es. vendite Italia ed estero).",
                  style="Secondario.TLabel").pack(anchor=tk.W)
        self._tree_reg = ttk.Treeview(s, columns=("codice", "descrizione", "tipo", "attivo"), show="headings", height=8)
        for col, titolo, w in (("codice", "Codice", 70), ("descrizione", "Descrizione", 240),
                               ("tipo", "Tipo", 120), ("attivo", "Attivo", 60)):
            self._tree_reg.heading(col, text=titolo)
            self._tree_reg.column(col, width=px(w), anchor=tk.W if col == "descrizione" else tk.CENTER)
        self._tree_reg.pack(fill=tk.BOTH, expand=True, pady=(px(6), 0))
        modulo = ttk.Frame(s)
        modulo.pack(fill=tk.X, pady=(px(8), 0))
        self._reg_codice = ttk.Entry(modulo, width=6)
        self._reg_descr = ttk.Entry(modulo, width=30)
        self._reg_tipo = ttk.Combobox(modulo, values=[VENDITE, ACQUISTI, CORRISPETTIVI], state="readonly", width=14)
        self._reg_tipo.set(VENDITE)
        for w in (self._reg_codice, self._reg_descr, self._reg_tipo):
            w.pack(side=tk.LEFT, padx=(0, px(6)))
        ttk.Button(modulo, text="Aggiungi", command=self._aggiungi_registro).pack(side=tk.LEFT)
        ttk.Button(s, text="Attiva / disattiva il registro selezionato", command=self._alterna_registro).pack(anchor=tk.W, pady=(px(6), 0))
        self._popola_registri()

    def _popola_registri(self):
        self._tree_reg.delete(*self._tree_reg.get_children())
        for r in self.modulo.get_registri(solo_attivi=False):
            self._tree_reg.insert("", tk.END, iid=str(r["id"]),
                                  values=(r["codice"], r["descrizione"], r["tipo"].capitalize(), "sì" if r["attivo"] else "no"))

    def _aggiungi_registro(self):
        codice, descr = self._reg_codice.get().strip(), self._reg_descr.get().strip()
        if not codice or not descr:
            messagebox.showerror("Errore", "Indicare codice e descrizione del registro.", parent=self)
            return
        try:
            self.modulo.salva_registro(codice, descr, self._reg_tipo.get())
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aggiungere il registro:\n{e}", parent=self)
            return
        self._reg_codice.delete(0, tk.END)
        self._reg_descr.delete(0, tk.END)
        self._popola_registri()

    def _alterna_registro(self):
        sel = self._tree_reg.selection()
        if not sel:
            return
        r = self.modulo.get_registro(int(sel[0]))
        self.modulo.salva_registro(r["codice"], r["descrizione"], r["tipo"], r["id"], attivo=not r["attivo"])
        self._popola_registri()

    def _scheda_aliquote(self, schede):
        s = ttk.Frame(schede, padding=px(12))
        schede.add(s, text="Aliquote")
        self._tree_al = ttk.Treeview(s, columns=("codice", "descrizione", "perc", "natura", "attiva"), show="headings", height=9)
        for col, titolo, w in (("codice", "Codice", 70), ("descrizione", "Descrizione", 240), ("perc", "%", 60),
                               ("natura", "Natura", 70), ("attiva", "Attiva", 60)):
            self._tree_al.heading(col, text=titolo)
            self._tree_al.column(col, width=px(w), anchor=tk.W if col == "descrizione" else tk.CENTER)
        self._tree_al.pack(fill=tk.BOTH, expand=True)
        modulo = ttk.Frame(s)
        modulo.pack(fill=tk.X, pady=(px(8), 0))
        self._al_codice = ttk.Entry(modulo, width=7)
        self._al_descr = ttk.Entry(modulo, width=26)
        self._al_perc = ttk.Entry(modulo, width=6)
        self._al_natura = ttk.Entry(modulo, width=6)
        for testo, w in (("Codice", self._al_codice), ("Descrizione", self._al_descr), ("%", self._al_perc), ("Natura", self._al_natura)):
            ttk.Label(modulo, text=testo, style="Secondario.TLabel").pack(side=tk.LEFT, padx=(0, px(3)))
            w.pack(side=tk.LEFT, padx=(0, px(6)))
        ttk.Button(modulo, text="Aggiungi", command=self._aggiungi_aliquota).pack(side=tk.LEFT)
        ttk.Button(s, text="Attiva / disattiva l'aliquota selezionata", command=self._alterna_aliquota).pack(anchor=tk.W, pady=(px(6), 0))
        self._popola_aliquote()

    def _popola_aliquote(self):
        self._tree_al.delete(*self._tree_al.get_children())
        for a in self.modulo.get_aliquote(solo_attive=False):
            self._tree_al.insert("", tk.END, iid=str(a["id"]), values=(
                a["codice"], a["descrizione"], f"{a['percentuale']:g}", a["natura"] or "", "sì" if a["attiva"] else "no"))

    def _aggiungi_aliquota(self):
        try:
            perc = float(self._al_perc.get().replace(",", ".") or 0)
            codice, descr = self._al_codice.get().strip(), self._al_descr.get().strip()
            if not codice or not descr:
                raise ValueError("Indicare codice e descrizione dell'aliquota.")
            if perc == 0 and not self._al_natura.get().strip():
                raise ValueError("Un'aliquota allo 0% richiede la natura (es. N4 esenti).")
            self.modulo.salva_aliquota(codice, descr, perc, self._al_natura.get().strip() or None)
        except Exception as e:
            messagebox.showerror("Errore", str(e), parent=self)
            return
        for w in (self._al_codice, self._al_descr, self._al_perc, self._al_natura):
            w.delete(0, tk.END)
        self._popola_aliquote()

    def _alterna_aliquota(self):
        sel = self._tree_al.selection()
        if not sel:
            return
        a = self.modulo.get_aliquota(int(sel[0]))
        self.modulo.salva_aliquota(a["codice"], a["descrizione"], a["percentuale"], a["natura"], a["id"], attiva=not a["attiva"])
        self._popola_aliquote()

    def _scheda_azienda(self, schede):
        s = ttk.Frame(schede, padding=px(12))
        schede.add(s, text="Azienda")
        ttk.Label(s, text="Dati riportati nell'intestazione dei registri e delle stampe fiscali.",
                  style="Secondario.TLabel").grid(row=0, column=0, columnspan=2, sticky=tk.W)
        self._azienda = {}
        for i, (chiave, testo) in enumerate((("denominazione", "Ragione sociale"), ("partita_iva", "Partita IVA"),
                                             ("codice_fiscale", "Codice fiscale"), ("indirizzo", "Sede")), 1):
            ttk.Label(s, text=testo).grid(row=i, column=0, sticky=tk.W, pady=px(3))
            e = ttk.Entry(s, width=40)
            e.insert(0, self.db.get_impostazione(f"azienda_{chiave}") or "")
            e.grid(row=i, column=1, sticky=tk.W, padx=(px(8), 0))
            self._azienda[chiave] = e

    def _on_salva(self):
        self.db.set_impostazione("iva_periodicita", self._periodicita.get())
        for ruolo, cb in self._ruoli.items():
            self.modulo.imposta_conto_ruolo(ruolo, self._map.get(cb.get()))
        rc = next((r for r in self.modulo.get_registri(VENDITE) if f"{r['codice']} - {r['descrizione']}" == self._reg_rc.get()), None)
        self.db.set_impostazione("iva_registro_reverse", rc["id"] if rc else None)
        for chiave, e in self._azienda.items():
            self.db.set_impostazione(f"azienda_{chiave}", e.get().strip() or None)
        self.destroy()


# --- Moduli facoltativi ---

class ModuliDialog(tk.Toplevel):
    """Attiva o spegne i moduli IVA e bilancio. Spenti, il programma funziona come prima."""

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.cambiato = False
        self.title("Moduli")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        f = ttk.Frame(self, padding=px(18))
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="Funzioni facoltative", style="Sottotitolo.TLabel").pack(anchor=tk.W)
        ttk.Label(f, wraplength=px(460), justify=tk.LEFT, style="Nota.TLabel",
                  text="Si attivano per questo archivio. Spegnendole non si perde nulla: i dati restano "
                       "e il programma torna a funzionare come prima.").pack(anchor=tk.W, pady=(px(4), px(10)))
        self._iva = tk.BooleanVar(value=db.modulo_attivo("iva"))
        self._bilancio = tk.BooleanVar(value=db.modulo_attivo("bilancio"))
        ttk.Checkbutton(f, variable=self._iva, text="Gestione IVA").pack(anchor=tk.W)
        ttk.Label(f, wraplength=px(440), justify=tk.LEFT, style="Secondario.TLabel",
                  text="Fatture di acquisto e vendita, note di credito, corrispettivi, reverse charge, IVA "
                       "indetraibile; registri IVA configurabili e stampabili; liquidazione mensile o "
                       "trimestrale.").pack(anchor=tk.W, padx=(px(24), 0), pady=(0, px(10)))
        ttk.Checkbutton(f, variable=self._bilancio, text="Bilancio civilistico").pack(anchor=tk.W)
        ttk.Label(f, wraplength=px(440), justify=tk.LEFT, style="Secondario.TLabel",
                  text="Stato patrimoniale e conto economico secondo il Codice civile (ordinario, abbreviato, "
                       "micro-imprese). Si collegano i conti alle voci di bilancio, anche solo in parte.").pack(
            anchor=tk.W, padx=(px(24), 0))
        btn = ttk.Frame(f)
        btn.pack(fill=tk.X, pady=(px(16), 0))
        ttk.Button(btn, text="Salva", style="Accent.TButton", command=self._on_salva).pack(side=tk.RIGHT)
        ttk.Button(btn, text="Annulla", command=self.destroy).pack(side=tk.RIGHT, padx=px(6))
        _centra(self, parent)

    def _on_salva(self):
        if self._iva.get() and not self.db.modulo_attivo("iva"):
            creati = ModuloIva(self.db).prepara()
            if creati:
                messagebox.showinfo(
                    "Gestione IVA attivata",
                    "Per la gestione IVA sono stati aggiunti:\n- " + "\n- ".join(creati) +
                    "\n\nControlla conti, registri, aliquote e dati dell'azienda in IVA > Impostazioni IVA.",
                    parent=self)
        for nome, var in (("iva", self._iva), ("bilancio", self._bilancio)):
            if var.get() != self.db.modulo_attivo(nome):
                self.db.imposta_modulo(nome, var.get())
                self.cambiato = True
        self.destroy()
