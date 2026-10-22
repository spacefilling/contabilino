"""
Contabilino - Finestre del modulo bilancio
Collegamento (facoltativo) dei conti alle voci del bilancio civilistico e
bilancio d'esercizio negli schemi ordinario, abbreviato e micro-imprese.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import bilancio_schemi as bs
from bilancio import ATTENZIONE, ERRORE, PRECEDENTE, calcola_bilancio, senza_voci_nulle
from tema import TESTO_SECONDARIO, ERRORE as COLORE_ERRORE, px
from widgets import format_importo


def _centra(finestra, parent):
    finestra.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - finestra.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - finestra.winfo_height()) // 5
    finestra.geometry(f"+{max(0, x)}+{max(0, y)}")


def _voce_breve(codice):
    """ "SPA.C.IV.1 · 1) depositi bancari e postali" (il percorso completo è troppo lungo)."""
    voce = bs.VOCI_ORDINARIO.get(codice)
    if not voce:
        return codice or ""
    padre = bs.VOCI_ORDINARIO.get(voce.padre) if voce.padre else None
    etichetta = voce.etichetta
    if padre and voce.genere == bs.FOGLIA and padre.genere != bs.SEZIONE and codice.split(".")[-1] in ("entro", "oltre"):
        etichetta = f"{padre.etichetta.split(',')[0]} – {voce.etichetta}"
    return f"{codice} · {etichetta}"


def _voci_per_tipo(tipo):
    """Foglie dello schema ordinario adatte al tipo del conto: stato patrimoniale o conto economico."""
    prefissi = ("SPA", "SPP") if tipo in ("ATTIVO", "PASSIVO") else ("CE",)
    return [c for c, _p in bs.voci_collegabili() if c.split(".")[0] in prefissi]


# Proposte di collegamento per i conti senza voce: (parole nel nome, tipi, voce, voce per il saldo opposto, rettifica)
PROPOSTE = [
    (("fondo amm", "f.do amm"), ("ATTIVO", "PASSIVO"), None, None, True),
    (("cassa", "contanti"), ("ATTIVO",), "SPA.C.IV.3", None, False),
    (("banca", "c/c", "conto corrente", "posta"), ("ATTIVO",), "SPA.C.IV.1", "SPP.D.4.entro", False),
    (("crediti clienti", "clienti", "crediti v/clienti"), ("ATTIVO", "PASSIVO"), "SPA.C.II.1.entro", "SPP.D.6.entro", False),
    (("iva su acquisti", "iva a credito", "iva c/acquisti"), ("ATTIVO",), "SPA.C.II.5-bis.entro", None, False),
    (("erario c/iva",), ("ATTIVO", "PASSIVO"), "SPP.D.12.entro", "SPA.C.II.5-bis.entro", False),
    (("rimanenze", "magazzino"), ("ATTIVO",), "SPA.C.I.4", None, False),
    (("risconti attivi", "ratei attivi"), ("ATTIVO",), "SPA.D", None, False),
    (("fabbricati", "immobili", "terreni"), ("ATTIVO",), "SPA.B.II.1", None, False),
    (("impianti", "macchinari"), ("ATTIVO",), "SPA.B.II.2", None, False),
    (("attrezzature",), ("ATTIVO",), "SPA.B.II.3", None, False),
    (("mobili", "arredi", "automezzi", "autovetture", "computer", "macchine d'ufficio"), ("ATTIVO",), "SPA.B.II.4", None, False),
    (("software", "marchi", "brevetti"), ("ATTIVO",), "SPA.B.I.3", None, False),
    (("debiti fornitori", "fornitori", "debiti v/fornitori"), ("PASSIVO", "ATTIVO"), "SPP.D.7.entro", "SPA.C.II.5-quater.entro", False),
    (("iva su vendite", "iva a debito", "iva c/vendite", "ritenute", "debiti tributari", "ires", "irap", "erario"),
     ("PASSIVO",), "SPP.D.12.entro", "SPA.C.II.5-bis.entro", False),
    (("inps", "inail", "previdenz"), ("PASSIVO",), "SPP.D.13.entro", None, False),
    (("mutu", "finanziamento banca", "debiti v/banche", "debiti verso banche"), ("PASSIVO",), "SPP.D.4.entro", None, False),
    (("finanziamento soci", "finanziamenti soci", "soci c/finanziamento"), ("PASSIVO",), "SPP.D.3.entro", None, False),
    (("capitale sociale", "capitale"), ("PASSIVO",), "SPP.A.I", None, False),
    (("riserva legale",), ("PASSIVO",), "SPP.A.IV", None, False),
    (("riserva straordinaria", "riserva"), ("PASSIVO",), "SPP.A.VI.straordinaria", None, False),
    (("utile d'esercizio", "utile dell'esercizio", "perdita d'esercizio"), ("PASSIVO",), "SPP.A.IX", None, False),
    (("portati a nuovo", "patrimonio netto", "bilancio di apertura", "apertura"), ("PASSIVO",), "SPP.A.VIII", None, False),
    (("trattamento di fine rapporto", "tfr"), ("PASSIVO",), "SPP.C", None, False),
    (("ratei passivi", "risconti passivi"), ("PASSIVO",), "SPP.E", None, False),
    (("fondo",), ("PASSIVO",), "SPP.B.4", None, False),
    (("salari", "stipendi", "personale"), ("COSTO",), "CE.B.9.a", None, False),
    (("oneri sociali", "contributi inps"), ("COSTO",), "CE.B.9.b", None, False),
    (("tfr", "trattamento di fine rapporto"), ("COSTO",), "CE.B.9.c", None, False),
    (("affitt", "locazion", "noleggi", "leasing", "canoni"), ("COSTO",), "CE.B.8", None, False),
    (("materie prime", "merci", "acquisti", "materiale di consumo", "materiali"), ("COSTO",), "CE.B.6", None, False),
    (("ammortamento immobilizzazioni immateriali", "amm.to immateriali"), ("COSTO",), "CE.B.10.a", None, False),
    (("ammortament",), ("COSTO",), "CE.B.10.b", None, False),
    (("interessi passivi", "oneri finanziari"), ("COSTO",), "CE.C.17.altri", None, False),
    (("ires", "irap", "imposte sul reddito"), ("COSTO",), "CE.20.correnti", None, False),
    (("utenze", "energia", "consulenz", "manutenzion", "trasport", "pubblicit", "assicuraz", "servizi",
      "telefon", "spese bancarie", "commissioni"), ("COSTO",), "CE.B.7", None, False),
    (("imposte", "tasse", "bolli", "sanzioni", "oneri diversi"), ("COSTO",), "CE.B.14", None, False),
    (("interessi attivi", "proventi finanziari"), ("RICAVO",), "CE.C.16.d.altri", None, False),
    (("contributi",), ("RICAVO",), "CE.A.5.a", None, False),
    (("sopravvenienze", "plusvalenz", "altri ricavi", "rimborsi"), ("RICAVO",), "CE.A.5.b", None, False),
    (("ricavi", "vendite", "prestazioni", "corrispettivi", "incassi", "fatturato"), ("RICAVO",), "CE.A.1", None, False),
]


def proponi(conto):
    """Proposta (voce, voce per il saldo opposto, rettifica) per un conto dal suo nome e tipo, o None."""
    nome = conto["nome"].lower()
    for parole, tipi, voce, opposta, rettifica in PROPOSTE:
        if conto["tipo"] in tipi and any(p in nome for p in parole):
            if rettifica:
                return None  # fondo ammortamento: la voce è quella del bene, da scegliere a mano
            return voce, opposta, False
    return None


class CollegaContiDialog(tk.Toplevel):
    """
    Collega i conti alle voci dello schema ordinario. È facoltativo e si può fare
    anche solo in parte: un sottoconto senza voce prende quella del suo conto padre,
    e i conti con saldo non collegati sono segnalati nel bilancio.
    """

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("Collega i conti alle voci di bilancio")
        self.transient(parent)
        self.grab_set()

        f = ttk.Frame(self, padding=px(16))
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, wraplength=px(760), justify=tk.LEFT, style="Nota.TLabel",
                  text="Per il bilancio civilistico ogni conto va collegato a una voce dello schema ordinario "
                       "(artt. 2424 e 2425 c.c.); l'abbreviato e le micro-imprese si ricavano da solo. "
                       "Un sottoconto senza voce usa quella del padre. Non è obbligatorio: i conti non "
                       "collegati vengono segnalati quando calcoli il bilancio.").pack(anchor=tk.W)

        cols = ("tipo", "voce", "note")
        self.tree = ttk.Treeview(f, columns=cols, show="tree headings", height=16, selectmode="browse")
        self.tree.heading("#0", text="Conto", anchor=tk.W)
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("voce", text="Voce di bilancio", anchor=tk.W)
        self.tree.heading("note", text="Note", anchor=tk.W)
        self.tree.column("#0", width=px(250))
        self.tree.column("tipo", width=px(80), anchor=tk.CENTER, stretch=False)
        self.tree.column("voce", width=px(330))
        self.tree.column("note", width=px(170))
        self.tree.tag_configure("proposta", foreground="#8a5a00")
        self.tree.tag_configure("ereditata", foreground=TESTO_SECONDARIO)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(px(10), 0))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._mostra_selezionato())

        modifica = ttk.LabelFrame(f, text="Conto selezionato", padding=px(10))
        modifica.pack(fill=tk.X, pady=(px(10), 0))
        self._nome = ttk.Label(modifica, style="Forte.TLabel")
        self._nome.grid(row=0, column=0, columnspan=3, sticky=tk.W)
        ttk.Label(modifica, text="Voce", style="Secondario.TLabel").grid(row=1, column=0, sticky=tk.W, pady=(px(4), 0))
        self._voce = ttk.Combobox(modifica, state="readonly", width=80, height=20)
        self._voce.grid(row=2, column=0, columnspan=3, sticky=tk.W + tk.E)
        ttk.Label(modifica, text="Se il saldo è dalla parte opposta (es. banca in rosso: debiti verso banche)",
                  style="Secondario.TLabel").grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(px(4), 0))
        self._opposta = ttk.Combobox(modifica, state="readonly", width=80, height=20)
        self._opposta.grid(row=4, column=0, columnspan=3, sticky=tk.W + tk.E)
        self._rettifica = tk.BooleanVar()
        ttk.Checkbutton(modifica, variable=self._rettifica,
                        text="Conto di rettifica (es. fondo ammortamento: il saldo riduce la voce)").grid(
            row=5, column=0, columnspan=3, sticky=tk.W, pady=(px(4), 0))
        btn = ttk.Frame(modifica)
        btn.grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=(px(8), 0))
        ttk.Button(btn, text="Applica", style="Accent.TButton", command=self._applica).pack(side=tk.LEFT)
        ttk.Button(btn, text="Togli il collegamento", command=self._togli).pack(side=tk.LEFT, padx=px(6))

        piede = ttk.Frame(f)
        piede.pack(fill=tk.X, pady=(px(10), 0))
        ttk.Button(piede, text="Proponi le voci dei conti non collegati...", command=self._proponi).pack(side=tk.LEFT)
        self._conteggio = ttk.Label(piede, style="Secondario.TLabel")
        self._conteggio.pack(side=tk.LEFT, padx=px(12))
        ttk.Button(piede, text="Chiudi", command=self.destroy).pack(side=tk.RIGHT)
        self.bind("<Escape>", lambda e: self.destroy())
        self._proposte = {}
        self._popola()
        _centra(self, parent)

    def _popola(self, seleziona=None):
        self.tree.delete(*self.tree.get_children())
        conti = self.db.get_conti()
        per_id = {c["id"]: c for c in conti}
        collegati = 0
        for c in conti:
            voce, nota, tag = c["voce_bilancio"], [], ()
            proposta = self._proposte.get(c["id"])
            if proposta and not c["voce_bilancio"]:
                voce, tag = proposta[0], ("proposta",)
                nota.append("proposta, da confermare")
            elif not voce and c["padre_id"]:
                padre = per_id[c["padre_id"]]
                voce_padre = padre["voce_bilancio"] or (self._proposte.get(padre["id"]) or (None,))[0]
                if voce_padre:
                    voce, tag = voce_padre, ("ereditata",)
                    nota.append("dal conto padre" + ("" if padre["voce_bilancio"] else " (proposta)"))
            if c["rettifica"]:
                nota.append("rettifica")
            if c["voce_bilancio_opposta"]:
                nota.append("saldo opposto: " + c["voce_bilancio_opposta"])
            if c["voce_bilancio"]:
                collegati += 1
            genitore = str(c["padre_id"]) if c["padre_id"] and self.tree.exists(str(c["padre_id"])) else ""
            self.tree.insert(genitore, tk.END, iid=str(c["id"]), text=f"{c['codice']}   {c['nome']}", open=True,
                             tags=tag, values=(c["tipo"], _voce_breve(voce) if voce else "—", ", ".join(nota)))
        self._conteggio.config(text=f"{collegati} conti collegati su {len(conti)}")
        if seleziona and self.tree.exists(str(seleziona)):
            self.tree.selection_set(str(seleziona))
            self.tree.see(str(seleziona))

    def _selezionato(self):
        sel = self.tree.selection()
        return self.db.get_conto(int(sel[0])) if sel else None

    def _mostra_selezionato(self):
        c = self._selezionato()
        if not c:
            return
        voci = [_voce_breve(v) for v in _voci_per_tipo(c["tipo"])]
        tutte = [_voce_breve(v) for v, _p in bs.voci_collegabili()]
        self._voce.configure(values=[""] + voci)
        self._opposta.configure(values=["(nessuna)"] + tutte)
        self._nome.config(text=f"{c['codice']} - {c['nome']}  ({c['tipo']})")
        proposta = self._proposte.get(c["id"])
        voce = c["voce_bilancio"] or (proposta[0] if proposta else "")
        opposta = c["voce_bilancio_opposta"] or (proposta[1] if proposta else None)
        self._voce.set(_voce_breve(voce) if voce else "")
        self._opposta.set(_voce_breve(opposta) if opposta else "(nessuna)")
        self._rettifica.set(bool(c["rettifica"]))

    @staticmethod
    def _codice(testo):
        return testo.split(" · ")[0] if testo and testo != "(nessuna)" else None

    def _applica(self):
        c = self._selezionato()
        if not c:
            return
        voce = self._codice(self._voce.get())
        if not voce:
            messagebox.showwarning("Collegamento", "Scegli la voce di bilancio (oppure usa \"Togli il collegamento\").", parent=self)
            return
        self.db.set_collegamento_bilancio(c["id"], voce, self._codice(self._opposta.get()), self._rettifica.get())
        self._proposte.pop(c["id"], None)
        self._popola(seleziona=c["id"])

    def _togli(self):
        c = self._selezionato()
        if c:
            self.db.set_collegamento_bilancio(c["id"], None, None, False)
            self._proposte.pop(c["id"], None)
            self._popola(seleziona=c["id"])

    def _proponi(self):
        """Propone le voci dei conti non collegati dal nome e dal tipo; si applicano solo confermando."""
        self._proposte = {}
        for c in self.db.get_conti():
            if c["voce_bilancio"]:
                continue
            proposta = proponi(c)
            if proposta:
                self._proposte[c["id"]] = proposta
        self._popola()
        if not self._proposte:
            messagebox.showinfo("Proposte", "Nessuna proposta: i conti non collegati hanno nomi che non "
                                            "permettono di indovinare la voce. Collegali a mano.", parent=self)
            return
        if messagebox.askyesno(
                "Proposte",
                f"Ci sono {len(self._proposte)} proposte, in arancione nell'elenco.\n\n"
                "Applicarle tutte? (Puoi anche controllarle una per una e applicarle con \"Applica\".)",
                parent=self):
            for conto_id, (voce, opposta, rettifica) in self._proposte.items():
                self.db.set_collegamento_bilancio(conto_id, voce, opposta, rettifica)
            self._proposte = {}
            self._popola()


class BilancioDialog(tk.Toplevel):
    """Bilancio d'esercizio: anteprima nei tre schemi, controlli e stampa."""

    def __init__(self, parent, db, esercizio_id, esporta):
        super().__init__(parent)
        self.db = db
        self._esporta = esporta
        self.title("Bilancio d'esercizio")
        self.transient(parent)
        self.grab_set()
        self.bilancio = None

        self._esercizi = {e["descrizione"]: e for e in db.get_esercizi()}
        f = ttk.Frame(self, padding=px(16))
        f.pack(fill=tk.BOTH, expand=True)
        barra = ttk.Frame(f)
        barra.pack(fill=tk.X)
        ttk.Label(barra, text="Esercizio", style="Secondario.TLabel").pack(side=tk.LEFT)
        self._esercizio = ttk.Combobox(barra, values=list(self._esercizi), state="readonly", width=24)
        corrente = db.get_esercizio(esercizio_id) if esercizio_id else None
        self._esercizio.set(corrente["descrizione"] if corrente else next(iter(self._esercizi), ""))
        self._esercizio.pack(side=tk.LEFT, padx=(px(6), px(14)))
        self._esercizio.bind("<<ComboboxSelected>>", lambda e: self._calcola())
        self._schema = tk.StringVar(value="abbreviato")
        for valore, testo in (("ordinario", "Ordinario"), ("abbreviato", "Abbreviato"), ("micro", "Micro-imprese")):
            ttk.Radiobutton(barra, text=testo, value=valore, variable=self._schema,
                            command=self._mostra).pack(side=tk.LEFT, padx=(0, px(8)))

        opzioni = ttk.Frame(f)
        opzioni.pack(fill=tk.X, pady=(px(6), 0))
        self._confronto = tk.BooleanVar(value=True)
        self._nulle = tk.BooleanVar(value=False)
        self._unita = tk.BooleanVar(value=False)
        ttk.Checkbutton(opzioni, text="Confronto con l'esercizio precedente", variable=self._confronto,
                        command=self._calcola).pack(side=tk.LEFT)
        ttk.Checkbutton(opzioni, text="Mostra le voci a zero", variable=self._nulle,
                        command=self._mostra).pack(side=tk.LEFT, padx=px(12))
        ttk.Checkbutton(opzioni, text="Importi all'unità di euro", variable=self._unita,
                        command=self._calcola).pack(side=tk.LEFT)

        self.tree = ttk.Treeview(f, columns=("corrente", "precedente"), show="tree headings", height=18)
        self.tree.heading("#0", text="Voce", anchor=tk.W)
        self.tree.heading("corrente", text="Esercizio")
        self.tree.heading("precedente", text="Precedente")
        self.tree.column("#0", width=px(560))
        self.tree.column("corrente", width=px(130), anchor=tk.E, stretch=False)
        self.tree.column("precedente", width=px(130), anchor=tk.E, stretch=False)
        self.tree.tag_configure("forte", font="Contabilino.Forte")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(px(10), 0))
        self._sintesi = ttk.Label(f, style="Forte.TLabel")
        self._sintesi.pack(anchor=tk.W, pady=(px(6), 0))

        ttk.Label(f, text="Controlli", style="Secondario.TLabel").pack(anchor=tk.W, pady=(px(8), 0))
        self.avvisi = ttk.Treeview(f, columns=("messaggio",), show="tree", height=5)
        self.avvisi.column("#0", width=px(110), stretch=False)
        self.avvisi.column("messaggio", width=px(710))
        self.avvisi.tag_configure(ERRORE, foreground=COLORE_ERRORE)
        self.avvisi.tag_configure(ATTENZIONE, foreground="#8a5a00")
        self.avvisi.pack(fill=tk.X)

        btn = ttk.Frame(f)
        btn.pack(fill=tk.X, pady=(px(10), 0))
        ttk.Button(btn, text="Stampa PDF...", style="Accent.TButton", command=lambda: self._on_esporta("pdf")).pack(side=tk.LEFT)
        ttk.Button(btn, text="Excel...", command=lambda: self._on_esporta("xlsx")).pack(side=tk.LEFT, padx=px(6))
        ttk.Button(btn, text="CSV...", command=lambda: self._on_esporta("csv")).pack(side=tk.LEFT)
        ttk.Button(btn, text="Chiudi", command=self.destroy).pack(side=tk.RIGHT)
        self.bind("<Escape>", lambda e: self.destroy())
        self._calcola()
        _centra(self, parent)

    def _esercizio_scelto(self):
        return self._esercizi.get(self._esercizio.get())

    def _calcola(self):
        esercizio = self._esercizio_scelto()
        if not esercizio:
            return
        mappa, rettifiche, opposte = self.db.get_collegamenti_bilancio()
        self._precedente = self.db.get_esercizio_precedente(esercizio["id"]) if self._confronto.get() else None
        self.bilancio = calcola_bilancio(
            self.db.get_saldi(esercizio["id"]), mappa,
            self.db.get_saldi(self._precedente["id"]) if self._precedente else None,
            rettifiche=rettifiche, voci_saldo_opposto=opposte, unita_di_euro=self._unita.get(),
        )
        self.avvisi.delete(*self.avvisi.get_children())
        for a in self.bilancio.avvisi:
            prefisso = "(esercizio precedente) " if a.esercizio == PRECEDENTE else ""
            self.avvisi.insert("", tk.END, text=a.gravita.capitalize(), values=(prefisso + a.messaggio,), tags=(a.gravita,))
        if not self.bilancio.avvisi:
            self.avvisi.insert("", tk.END, text="OK", values=("Nessuna segnalazione.",))
        self._mostra()

    def _mostra(self):
        if not self.bilancio:
            return
        prospetto = getattr(self.bilancio, self._schema.get())
        con_prec = prospetto.valori_precedenti is not None
        self.tree.heading("precedente", text=self._precedente["descrizione"] if con_prec and self._precedente else "")
        self.tree.heading("corrente", text=self._esercizio.get())
        self.tree.delete(*self.tree.get_children())

        def importo(x):
            return "" if x is None else (format_importo(x) or "0,00")

        for titolo, righe in (("STATO PATRIMONIALE", prospetto.stato_patrimoniale),
                              ("CONTO ECONOMICO", prospetto.conto_economico)):
            self.tree.insert("", tk.END, text=titolo, tags=("forte",))
            if not self._nulle.get():
                righe = senza_voci_nulle(righe)
            for r in righe:
                forte = r.genere in ("INTESTAZIONE", "TOTALE", "RISULTATO")
                self.tree.insert("", tk.END, text="    " * (r.livello + 1) + r.etichetta,
                                 values=(importo(r.importo), importo(r.importo_precedente) if con_prec else ""),
                                 tags=("forte",) if forte else ())
        risultato = prospetto.risultato
        self._sintesi.config(
            text=f"Totale attivo {format_importo(prospetto.totale_attivo) or '0,00'}   ·   "
                 f"Totale passivo {format_importo(prospetto.totale_passivo) or '0,00'}   ·   "
                 f"{'Utile' if risultato >= 0 else 'Perdita'} {format_importo(abs(risultato)) or '0,00'}   ·   "
                 + ("quadra" if self.bilancio.quadra else "NON QUADRA: vedi i controlli"))

    def _on_esporta(self, formato):
        from export import report_bilancio
        esercizio = self._esercizio_scelto()
        if not esercizio or not self.bilancio:
            return
        errori = [a for a in self.bilancio.avvisi if a.gravita == ERRORE and a.esercizio != PRECEDENTE]
        if errori and not messagebox.askyesno(
                "Bilancio con errori", "Il bilancio ha errori (vedi i controlli, per esempio non quadra).\n"
                                       "Esportarlo comunque?", parent=self):
            return
        schema = self._schema.get()
        report = report_bilancio(self.db, self.bilancio, schema, esercizio, self._precedente, voci_nulle=self._nulle.get())
        self._esporta(report, f"bilancio_{schema}_{esercizio['descrizione'].replace(' ', '_').replace('/', '-')}", formato)
