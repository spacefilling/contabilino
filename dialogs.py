"""
Contabilino - Finestre di dialogo
Gestione esercizi e piano dei conti (con gerarchia padre/figlio),
eliminazione e storno delle registrazioni, scelta dei conti da esportare.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from dateutils import (
    data_in_periodo,
    descrizione_default,
    fine_default,
    format_display,
    periodo_label,
)
from widgets import SmartDateEntry, format_importo


class GestioneEserciziDialog(tk.Toplevel):
    """Dialogo per gestire gli esercizi contabili."""

    def __init__(self, parent, db, current_esercizio_id=None):
        super().__init__(parent)
        self.db = db
        self.selected_id = current_esercizio_id

        self.title("Gestione Esercizi")
        self.geometry("740x360")
        self.resizable(True, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._refresh_list()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        cols = ("descrizione", "inizio", "fine", "stato")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=9)
        self.tree.heading("descrizione", text="Descrizione")
        self.tree.heading("inizio", text="Inizio")
        self.tree.heading("fine", text="Fine")
        self.tree.heading("stato", text="Stato")
        self.tree.column("descrizione", width=250)
        self.tree.column("inizio", width=100, anchor=tk.CENTER, stretch=False)
        self.tree.column("fine", width=100, anchor=tk.CENTER, stretch=False)
        self.tree.column("stato", width=80, anchor=tk.CENTER, stretch=False)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-Button-1>", lambda e: self._on_seleziona())

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="Nuovo", command=self._on_nuovo).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Modifica", command=self._on_modifica).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Chiudi/Riapri", command=self._on_toggle_chiudi).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Elimina", command=self._on_elimina).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Riporta saldi...", command=self._on_riporta_saldi).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Seleziona", command=self._on_seleziona).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Chiudi finestra", command=self.destroy).pack(side=tk.RIGHT, padx=3)

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        esercizi = self.db.get_esercizi()
        for e in esercizi:
            stato = "Chiuso" if e["data_chiusura"] else "Aperto"
            self.tree.insert("", tk.END, iid=str(e["id"]),
                             values=(e["descrizione"],
                                     format_display(e["data_inizio"]),
                                     format_display(e["data_fine"]),
                                     stato))
        if self.selected_id and self.tree.exists(str(self.selected_id)):
            self.tree.selection_set(str(self.selected_id))

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Selezionare un esercizio.", parent=self)
            return None
        return int(sel[0])

    def _on_nuovo(self):
        dlg = EsercizioDialog(self, self.db)
        self.wait_window(dlg)
        if dlg.result:
            descrizione, data_inizio, data_fine = dlg.result
            try:
                nuovo_id = self.db.crea_esercizio(descrizione, data_inizio, data_fine)
                self._refresh_list()
            except Exception as e:
                messagebox.showerror("Errore", str(e), parent=self)
                return
            self._proponi_riporto(nuovo_id)

    def _proponi_riporto(self, esercizio_id):
        """Nuovo esercizio: se il precedente ha saldi di attivo e passivo, chiede se riportarli."""
        precedente = self.db.get_esercizio_precedente(esercizio_id)
        if not precedente or not self.db.saldi_da_riportare(precedente["id"]):
            return
        if messagebox.askyesno(
            "Riporto dei saldi",
            f"Riportare i saldi di attivo e passivo (cassa, banca, crediti, debiti...)\n"
            f"dall'esercizio \"{precedente['descrizione']}\" all'inizio del nuovo esercizio?\n\n"
            "Si può fare anche più tardi con il pulsante \"Riporta saldi...\".",
            parent=self,
        ):
            self._riporta(esercizio_id, precedente)

    def _on_riporta_saldi(self):
        eid = self._get_selected_id()
        if not eid:
            return
        esercizio = self.db.get_esercizio(eid)
        if esercizio["data_chiusura"]:
            messagebox.showwarning("Attenzione", "L'esercizio è chiuso: per riportarvi i saldi va prima riaperto.", parent=self)
            return
        precedente = self.db.get_esercizio_precedente(eid)
        if not precedente:
            messagebox.showinfo("Riporto dei saldi", "Non c'è un esercizio precedente a questo da cui riportare i saldi.", parent=self)
            return
        self._riporta(eid, precedente)

    def _riporta(self, esercizio_id, precedente):
        dlg = RiportoSaldiDialog(self, self.db, esercizio_id, precedente["id"])
        self.wait_window(dlg)
        if not dlg.result:
            return
        messaggio = f"Registrati {dlg.result} saldi di apertura dall'esercizio \"{precedente['descrizione']}\"."
        # Se l'esercizio aveva già registrazioni, le aperture (al primo giorno) hanno numeri più alti
        fuori_ordine = self.db.conta_numeri_fuori_ordine(esercizio_id)
        if not fuori_ordine:
            messagebox.showinfo("Riporto dei saldi", messaggio, parent=self)
        elif messagebox.askyesno(
            "Riporto dei saldi",
            f"{messaggio}\n\n"
            "L'esercizio aveva già delle registrazioni: le aperture, datate al primo giorno,\n"
            "hanno numeri più alti. Rinumerare le registrazioni in ordine di data?\n"
            f"Cambia il numero di {fuori_ordine} registrazioni.",
            parent=self,
        ):
            self.db.rinumera_in_ordine_di_data(esercizio_id)

    def _on_modifica(self):
        eid = self._get_selected_id()
        if not eid:
            return
        esercizio = self.db.get_esercizio(eid)
        dlg = EsercizioDialog(self, self.db, esercizio=esercizio)
        self.wait_window(dlg)
        if dlg.result:
            descrizione, data_inizio, data_fine = dlg.result
            # Avvisa se il nuovo periodo lascia fuori registrazioni già inserite
            fuori = self.db.registrazioni_fuori_periodo(eid, data_inizio, data_fine)
            if fuori:
                conferma = messagebox.askyesno(
                    "Attenzione",
                    f"{fuori} registrazioni di questo esercizio hanno una data\n"
                    f"fuori dal periodo {periodo_label(data_inizio, data_fine)}.\n\n"
                    "Restano comunque nell'esercizio. Procedere ugualmente?",
                    parent=self,
                )
                if not conferma:
                    return
            try:
                self.db.modifica_esercizio(eid, descrizione, data_inizio, data_fine)
                self._refresh_list()
            except Exception as e:
                messagebox.showerror("Errore", str(e), parent=self)

    def _on_elimina(self):
        eid = self._get_selected_id()
        if not eid:
            return
        esercizio = self.db.get_esercizio(eid)
        if not messagebox.askyesno(
            "Conferma",
            f"Eliminare l'esercizio \"{esercizio['descrizione']}\"?",
            parent=self,
        ):
            return
        try:
            self.db.elimina_esercizio(eid)
            if self.selected_id == eid:
                self.selected_id = None
            self._refresh_list()
        except Exception as e:
            messagebox.showerror("Errore", str(e), parent=self)

    def _on_toggle_chiudi(self):
        eid = self._get_selected_id()
        if not eid:
            return
        esercizio = self.db.get_esercizio(eid)
        if esercizio["data_chiusura"]:
            if not messagebox.askyesno(
                "Riapri esercizio",
                f"Riaprire l'esercizio \"{esercizio['descrizione']}\"?\n\n"
                "Le sue registrazioni torneranno modificabili ed eliminabili:\n"
                "i report già stampati o consegnati potrebbero non corrispondere più.",
                parent=self,
            ):
                return
            self.db.riapri_esercizio(eid)
        else:
            if not messagebox.askyesno(
                "Chiudi esercizio",
                f"Chiudere l'esercizio \"{esercizio['descrizione']}\"?\n\n"
                "Le sue registrazioni non si potranno più aggiungere, modificare\n"
                "né eliminare (si potranno solo stornare). Si può riaprire in seguito.",
                parent=self,
            ):
                return
            self.db.chiudi_esercizio(eid, date.today().isoformat())
        self._refresh_list()

    def _on_seleziona(self):
        eid = self._get_selected_id()
        if eid:
            self.selected_id = eid
            self.destroy()


class EsercizioDialog(tk.Toplevel):
    """
    Dialogo per creare o modificare un esercizio contabile.
    Il periodo è libero: può coincidere con l'anno solare oppure essere
    a cavallo tra due anni (es. 01/07/2026 - 30/06/2027).
    """

    def __init__(self, parent, db, esercizio=None):
        super().__init__(parent)
        self.db = db
        self.result = None
        self._esercizio = esercizio

        self.title("Modifica Esercizio" if esercizio else "Nuovo Esercizio")
        self.geometry("430x270")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Data inizio:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.inizio_entry = SmartDateEntry(frame, width=14, on_change=self._on_inizio_change)
        self.inizio_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        ttk.Label(frame, text="Data fine:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.fine_entry = SmartDateEntry(frame, width=14, on_change=self._aggiorna_descrizione)
        self.fine_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(
            frame,
            text="Il periodo può essere a cavallo tra due anni\n(es. 01/07/2026 - 30/06/2027).",
            foreground="#555555",
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        ttk.Label(frame, text="Descrizione:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.desc_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.desc_var, width=30).grid(
            row=3, column=1, sticky=tk.W, pady=5
        )

        preset_frame = ttk.Frame(frame)
        preset_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        ttk.Label(preset_frame, text="Imposta rapida:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(preset_frame, text="Anno solare", width=12,
                   command=self._preset_anno_solare).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="1 luglio - 30 giugno", width=18,
                   command=self._preset_luglio_giugno).pack(side=tk.LEFT, padx=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Salva", command=self._on_salva).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=5)

        # Valori iniziali
        if self._esercizio:
            self.inizio_entry.set_iso_date(self._esercizio["data_inizio"])
            self.fine_entry.set_iso_date(self._esercizio["data_fine"])
            self.desc_var.set(self._esercizio["descrizione"])
        else:
            self._preset_anno_solare()
        self.inizio_entry.focus_set()

    # --- Automatismi ---

    def _on_inizio_change(self):
        """Propone la data di fine (12 mesi - 1 giorno) se non è già impostata."""
        inizio = self.inizio_entry.get_iso_date()
        if inizio and self.fine_entry.is_empty():
            self.fine_entry.set_iso_date(fine_default(inizio))
        self._aggiorna_descrizione()

    def _aggiorna_descrizione(self):
        """Aggiorna la descrizione proposta finché l'utente non ne scrive una sua."""
        inizio = self.inizio_entry.get_iso_date()
        fine = self.fine_entry.get_iso_date()
        if not inizio:
            return
        attuale = self.desc_var.get().strip()
        if attuale and attuale != getattr(self, "_proposta", ""):
            return  # descrizione personalizzata: non toccarla
        self._proposta = descrizione_default(inizio, fine)
        self.desc_var.set(self._proposta)

    def _preset_anno_solare(self):
        anno = date.today().year
        self._imposta_periodo(f"{anno}-01-01", f"{anno}-12-31")

    def _preset_luglio_giugno(self):
        oggi = date.today()
        anno = oggi.year if oggi.month >= 7 else oggi.year - 1
        self._imposta_periodo(f"{anno}-07-01", f"{anno + 1}-06-30")

    def _imposta_periodo(self, inizio_iso, fine_iso):
        self.inizio_entry.set_iso_date(inizio_iso)
        self.fine_entry.set_iso_date(fine_iso)
        self.desc_var.set(descrizione_default(inizio_iso, fine_iso))
        self._proposta = self.desc_var.get()

    # --- Salvataggio ---

    def _on_salva(self):
        data_inizio = self.inizio_entry.get_iso_date()
        data_fine = self.fine_entry.get_iso_date()

        if not data_inizio:
            messagebox.showerror("Errore", "Data di inizio non valida (usare GG/MM/AAAA).", parent=self)
            self.inizio_entry.focus_set()
            return
        if not data_fine:
            messagebox.showerror("Errore", "Data di fine non valida (usare GG/MM/AAAA).", parent=self)
            self.fine_entry.focus_set()
            return
        if data_fine <= data_inizio:
            messagebox.showerror(
                "Errore",
                "La data di fine deve essere successiva alla data di inizio.",
                parent=self,
            )
            self.fine_entry.focus_set()
            return

        descrizione = self.desc_var.get().strip()
        if not descrizione:
            descrizione = descrizione_default(data_inizio, data_fine)

        self.result = (descrizione, data_inizio, data_fine)
        self.destroy()


class GestioneContiDialog(tk.Toplevel):
    """Dialogo per gestire il piano dei conti con gerarchia padre/figlio."""

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db

        self.title("Gestione Piano dei Conti")
        self.geometry("550x450")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._refresh_list()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Treeview ad albero: mostra gerarchia conti/sottoconti
        cols = ("codice", "nome", "tipo")
        self.tree = ttk.Treeview(frame, columns=cols, show="tree headings", height=14)
        self.tree.heading("#0", text="")
        self.tree.heading("codice", text="Codice")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("tipo", text="Tipo")
        self.tree.column("#0", width=30, stretch=False)
        self.tree.column("codice", width=70, anchor=tk.CENTER)
        self.tree.column("nome", width=270)
        self.tree.column("tipo", width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Nuovo conto", command=self._on_nuovo).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Nuovo sottoconto", command=self._on_nuovo_sotto).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Modifica", command=self._on_modifica).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Elimina", command=self._on_elimina).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Chiudi", command=self.destroy).pack(side=tk.RIGHT, padx=3)

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Inserisci prima i conti padre, poi i sottoconti come figli nel treeview
        padri = self.db.get_conti_padri()
        for p in padri:
            pid = str(p["id"])
            self.tree.insert("", tk.END, iid=pid,
                             values=(p["codice"], p["nome"], p["tipo"]))
            sottoconti = self.db.get_sottoconti(p["id"])
            for s in sottoconti:
                self.tree.insert(pid, tk.END, iid=str(s["id"]),
                                 values=(s["codice"], s["nome"], s["tipo"]))
            # Espandi i padri che hanno figli
            if sottoconti:
                self.tree.item(pid, open=True)

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Selezionare un conto.", parent=self)
            return None
        return int(sel[0])

    def _on_nuovo(self):
        """Nuovo conto principale (senza padre)."""
        dlg = EditContoDialog(self, self.db)
        self.wait_window(dlg)
        if dlg.result:
            codice, nome, tipo, padre_id = dlg.result
            try:
                self.db.crea_conto(codice, nome, tipo, padre_id)
                self._refresh_list()
            except Exception as e:
                messagebox.showerror("Errore", str(e), parent=self)

    def _on_nuovo_sotto(self):
        """Nuovo sottoconto del conto selezionato."""
        padre_id = self._get_selected_id()
        if not padre_id:
            return
        # Se il conto selezionato è già un figlio, usa il suo padre
        conto_sel = self.db.get_conto(padre_id)
        if conto_sel["padre_id"]:
            padre_id = conto_sel["padre_id"]

        dlg = EditContoDialog(self, self.db, padre_id_default=padre_id)
        self.wait_window(dlg)
        if dlg.result:
            codice, nome, tipo, pid = dlg.result
            try:
                self.db.crea_conto(codice, nome, tipo, pid)
                self._refresh_list()
            except Exception as e:
                messagebox.showerror("Errore", str(e), parent=self)

    def _on_modifica(self):
        cid = self._get_selected_id()
        if not cid:
            return
        conto = self.db.get_conto(cid)
        dlg = EditContoDialog(self, self.db, conto=conto)
        self.wait_window(dlg)
        if dlg.result:
            codice, nome, tipo, padre_id = dlg.result
            try:
                self.db.modifica_conto(cid, codice, nome, tipo, padre_id)
                self._refresh_list()
            except Exception as e:
                messagebox.showerror("Errore", str(e), parent=self)

    def _on_elimina(self):
        cid = self._get_selected_id()
        if not cid:
            return
        try:
            # Verifica preventiva con messaggio chiaro
            if self.db.conto_ha_sottoconti(cid):
                messagebox.showerror(
                    "Errore",
                    "Impossibile eliminare: il conto ha sottoconti.\nEliminare prima i sottoconti.",
                    parent=self,
                )
                return
            if self.db.conto_ha_movimenti(cid):
                messagebox.showerror(
                    "Errore",
                    "Impossibile eliminare: il conto ha movimenti associati.",
                    parent=self,
                )
                return
            if messagebox.askyesno("Conferma", "Eliminare il conto selezionato?", parent=self):
                self.db.elimina_conto(cid)
                self._refresh_list()
        except Exception as e:
            messagebox.showerror("Errore", str(e), parent=self)


class EditContoDialog(tk.Toplevel):
    """Dialogo per creare o modificare un conto, con selezione padre opzionale."""

    def __init__(self, parent, db, conto=None, padre_id_default=None):
        super().__init__(parent)
        self.db = db
        self.result = None
        self._conto_id = conto["id"] if conto else None
        self._tipo_originale = conto["tipo"] if conto else None

        self.title("Modifica Conto" if conto else "Nuovo Conto")
        self.geometry("400x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui(conto, padre_id_default)

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self, conto, padre_id_default):
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Conto padre (dropdown)
        ttk.Label(frame, text="Conto padre:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.padre_var = tk.StringVar()
        padri = self.db.get_conti_padri()
        # Costruisci la mappa label → id
        self._padre_map = {"(nessuno - conto principale)": None}
        padre_labels = ["(nessuno - conto principale)"]
        for p in padri:
            # Non mostrare il conto stesso come possibile padre
            if self._conto_id and p["id"] == self._conto_id:
                continue
            label = f"{p['codice']} - {p['nome']}"
            self._padre_map[label] = p["id"]
            padre_labels.append(label)

        padre_cb = ttk.Combobox(
            frame, textvariable=self.padre_var,
            values=padre_labels, state="readonly", width=35,
        )
        padre_cb.grid(row=0, column=1, sticky=tk.W, pady=5)

        # Seleziona il padre corretto
        current_padre_id = None
        if conto and conto["padre_id"]:
            current_padre_id = conto["padre_id"]
        elif padre_id_default:
            current_padre_id = padre_id_default

        if current_padre_id:
            for label, pid in self._padre_map.items():
                if pid == current_padre_id:
                    self.padre_var.set(label)
                    break
        else:
            self.padre_var.set(padre_labels[0])

        # Codice
        ttk.Label(frame, text="Codice:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.codice_var = tk.StringVar(value=conto["codice"] if conto else "")
        ttk.Entry(frame, textvariable=self.codice_var, width=10).grid(
            row=1, column=1, sticky=tk.W, pady=5
        )

        # Nome
        ttk.Label(frame, text="Nome:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.nome_var = tk.StringVar(value=conto["nome"] if conto else "")
        ttk.Entry(frame, textvariable=self.nome_var, width=30).grid(
            row=2, column=1, sticky=tk.W, pady=5
        )

        # Tipo
        ttk.Label(frame, text="Tipo:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.tipo_var = tk.StringVar(value=conto["tipo"] if conto else "COSTO")
        tipo_cb = ttk.Combobox(
            frame, textvariable=self.tipo_var,
            values=["ATTIVO", "PASSIVO", "COSTO", "RICAVO"],
            state="readonly", width=15,
        )
        tipo_cb.grid(row=3, column=1, sticky=tk.W, pady=5)

        # Quando si cambia padre, eredita il tipo (anche per il padre proposto a un nuovo sottoconto)
        padre_cb.bind("<<ComboboxSelected>>", self._on_padre_changed)
        if not conto and current_padre_id:
            self._on_padre_changed()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Salva", command=self._on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _on_padre_changed(self, event=None):
        """Quando si seleziona un padre, imposta automaticamente il tipo."""
        padre_label = self.padre_var.get()
        padre_id = self._padre_map.get(padre_label)
        if padre_id:
            padre = self.db.get_conto(padre_id)
            if padre:
                self.tipo_var.set(padre["tipo"])

    def _on_save(self):
        codice = self.codice_var.get().strip()
        nome = self.nome_var.get().strip()
        tipo = self.tipo_var.get()
        padre_label = self.padre_var.get()
        padre_id = self._padre_map.get(padre_label)

        if not codice:
            messagebox.showerror("Errore", "Inserire il codice.", parent=self)
            return
        if not nome:
            messagebox.showerror("Errore", "Inserire il nome.", parent=self)
            return
        if padre_id:
            padre = self.db.get_conto(padre_id)
            if padre and padre["tipo"] != tipo and not messagebox.askyesno(
                "Tipo diverso dal conto padre",
                f"Il conto padre {padre['codice']} - {padre['nome']} è di tipo {padre['tipo']},\n"
                f"questo sottoconto di tipo {tipo}.\n\n"
                "Di solito un sottoconto ha lo stesso tipo del padre. Salvare comunque?",
                parent=self,
            ):
                return
        if self._conto_id and self._tipo_originale != tipo and self.db.conto_ha_movimenti(self._conto_id):
            if not messagebox.askyesno(
                "Cambio di tipo",
                f"Il conto ha già dei movimenti: passando da {self._tipo_originale} a {tipo}\n"
                "cambiano i report (Costi e Ricavi, Partitari) di tutti gli esercizi\n"
                "in cui compare, anche di quelli chiusi. Procedere?",
                parent=self,
            ):
                return
        self.result = (codice, nome, tipo, padre_id)
        self.destroy()


def _righe_dati(parent, righe, start_row=0):
    """Coppie etichetta/valore allineate in griglia dentro parent."""
    for i, (etichetta, valore) in enumerate(righe, start_row):
        ttk.Label(parent, text=f"{etichetta}:").grid(
            row=i, column=0, sticky=tk.W, padx=(0, 10), pady=1
        )
        ttk.Label(parent, text=valore, wraplength=380).grid(row=i, column=1, sticky=tk.W, pady=1)


def _invio(event, azione_predefinita):
    """Invio attiva il pulsante che ha il focus; altrimenti l'azione principale del dialogo."""
    if isinstance(event.widget, ttk.Button):
        event.widget.invoke()
    else:
        azione_predefinita()


class EliminaRegistrazioneDialog(tk.Toplevel):
    """
    Conferma dell'eliminazione di una registrazione, con i suoi dati completi.
    Chiede in modo esplicito se rinumerare le registrazioni successive e
    propone lo storno come alternativa.
    Alla chiusura: result = None (annullato), "elimina" oppure "storno";
    rinumera = True se le registrazioni successive vanno rinumerate.
    """

    def __init__(self, parent, registrazione, successive):
        super().__init__(parent)
        self.result = None
        self.rinumera = False
        self._reg = registrazione
        self._successive = successive
        self._rinumera_var = tk.BooleanVar(value=False)

        self.title("Elimina registrazione")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.bind("<Return>", lambda e: _invio(e, self._on_elimina))
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        reg = self._reg
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Eliminare questa registrazione?", font=("", 10, "bold")).pack(anchor=tk.W)

        dati = ttk.Frame(frame)
        dati.pack(fill=tk.X, pady=(8, 12))
        _righe_dati(dati, [
            ("N.", f"{reg['numero']} del {format_display(reg['data'])}"),
            ("Causale", reg["descrizione"]),
            ("Dare", f"{reg['dare_codice']} - {reg['dare_nome']}"),
            ("Avere", f"{reg['avere_codice']} - {reg['avere_nome']}"),
            ("Importo", format_importo(reg["importo"])),
        ])

        numerazione = ttk.LabelFrame(frame, text="Numerazione", padding=8)
        numerazione.pack(fill=tk.X)
        if self._successive:
            if self._successive == 1:
                successive = "la registrazione successiva scala"
            else:
                successive = f"le {self._successive} registrazioni successive scalano"
            ttk.Radiobutton(
                numerazione, variable=self._rinumera_var, value=False,
                text=f"Lascia i numeri come sono (il n. {reg['numero']} resta libero)",
            ).pack(anchor=tk.W, pady=1)
            ttk.Radiobutton(
                numerazione, variable=self._rinumera_var, value=True,
                text=f"Rinumera: {successive} di un numero",
            ).pack(anchor=tk.W, pady=1)
        else:
            ttk.Label(
                numerazione,
                text="È la registrazione con il numero più alto:\n"
                     "non ci sono registrazioni successive da rinumerare.",
            ).pack(anchor=tk.W)

        ttk.Label(
            frame,
            text="In alternativa puoi stornarla: la registrazione resta nel giornale\n"
                 "e se ne aggiunge una con i conti invertiti che la annulla.",
            foreground="#555555",
        ).pack(anchor=tk.W, pady=(10, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(15, 0))
        btn_elimina = ttk.Button(btn_frame, text="Elimina", command=self._on_elimina)
        btn_elimina.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Storno invece...", command=self._on_storno).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=5)
        btn_elimina.focus_set()

    def _on_elimina(self):
        self.result = "elimina"
        self.rinumera = self._rinumera_var.get()
        self.destroy()

    def _on_storno(self):
        self.result = "storno"
        self.destroy()


class StornoDialog(tk.Toplevel):
    """
    Storno di una registrazione: se ne aggiunge una nuova con gli stessi conti
    e lo stesso importo ma Dare e Avere invertiti, così l'effetto sui saldi si
    annulla e nel giornale restano sia l'originale sia la correzione.
    Lo storno va nell'esercizio che contiene la data scelta, che deve essere
    aperto: si può quindi stornare anche una registrazione di un esercizio chiuso.
    Alla chiusura: result = id della registrazione di storno (None se annullato).
    """

    def __init__(self, parent, db, registrazione):
        super().__init__(parent)
        self.db = db
        self.result = None
        self._reg = registrazione

        self.title("Storno registrazione")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.bind("<Return>", lambda e: _invio(e, self._on_registra))
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        reg = self._reg
        dare = f"{reg['dare_codice']} - {reg['dare_nome']}"
        avere = f"{reg['avere_codice']} - {reg['avere_nome']}"
        importo = format_importo(reg["importo"])

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        originale = ttk.LabelFrame(frame, text="Registrazione da stornare", padding=8)
        originale.pack(fill=tk.X)
        _righe_dati(originale, [
            ("N.", f"{reg['numero']} del {format_display(reg['data'])}"),
            ("Causale", reg["descrizione"]),
            ("Dare", dare),
            ("Avere", avere),
            ("Importo", importo),
        ])

        storno = ttk.LabelFrame(frame, text="Storno (stessi conti, Dare e Avere invertiti)", padding=8)
        storno.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(storno, text="Data:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        self.data_entry = SmartDateEntry(storno, width=14, on_change=self._aggiorna_esercizio)
        self.data_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.esercizio_label = ttk.Label(storno, foreground="#555555")
        self.esercizio_label.grid(row=1, column=1, sticky=tk.W)

        ttk.Label(storno, text="Causale:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        self.causale_var = tk.StringVar(
            value=f"Storno reg. n. {reg['numero']} del {format_display(reg['data'])} - {reg['descrizione']}"
        )
        ttk.Entry(storno, textvariable=self.causale_var, width=50).grid(
            row=2, column=1, sticky=tk.W, pady=2
        )

        _righe_dati(storno, [("Dare", avere), ("Avere", dare), ("Importo", importo)], start_row=3)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(15, 0))
        ttk.Button(btn_frame, text="Registra storno", command=self._on_registra).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.data_entry.set_iso_date(self._data_proposta())
        self._aggiorna_esercizio()
        self.data_entry.focus_set()

    def _data_proposta(self):
        """
        Oggi, se cade nell'esercizio della registrazione; altrimenti la data
        dell'originale, così lo storno resta nello stesso esercizio.
        Se quell'esercizio è chiuso lo storno va per forza in un altro: oggi.
        """
        oggi = date.today().isoformat()
        esercizio = self.db.get_esercizio(self._reg["esercizio_id"])
        if esercizio["data_chiusura"]:
            return oggi
        if data_in_periodo(oggi, esercizio["data_inizio"], esercizio["data_fine"]):
            return oggi
        return self._reg["data"]

    def _aggiorna_esercizio(self):
        """Mostra in quale esercizio finirà lo storno con la data scelta."""
        data = self.data_entry.get_iso_date()
        if not data:
            testo = "Data non valida (usare GG/MM/AAAA)."
        else:
            esercizio = self.db.get_esercizio_per_data(data)
            if not esercizio:
                testo = "Nessun esercizio comprende questa data."
            elif esercizio["data_chiusura"]:
                testo = f"{esercizio['descrizione']}: esercizio chiuso."
            else:
                testo = f"Verrà registrato in: {esercizio['descrizione']}"
        self.esercizio_label.config(text=testo)

    def _on_registra(self):
        self.data_entry._format()
        data = self.data_entry.get_iso_date()
        causale = self.causale_var.get().strip()
        if not data:
            messagebox.showerror("Errore", "Data non valida (usare GG/MM/AAAA).", parent=self)
            self.data_entry.focus_set()
            return
        if not causale:
            messagebox.showerror("Errore", "Inserire la causale.", parent=self)
            return
        try:
            self.result = self.db.storna_registrazione(self._reg["id"], data, causale)
        except ValueError as e:
            messagebox.showerror("Errore", str(e), parent=self)
            self.data_entry.focus_set()
            return
        self.destroy()



def chiave_codice(codice):
    """Ordine dei codici conto: numerico se il codice è un numero (99 prima di 100)."""
    codice = codice.strip()
    return (0, int(codice), "") if codice.isdigit() else (1, 0, codice.lower())


class SelezioneContiDialog(tk.Toplevel):
    """
    Scelta dei conti da esportare: tutti, oppure quelli spuntati nell'elenco.
    I conti si spuntano uno per uno (clic o barra spaziatrice), per intervallo
    di codici o dopo averli cercati per nome; spuntare un conto padre spunta
    anche i suoi sottoconti. Con solo_economici c'è anche la scelta
    "solo i conti di costo e ricavo" (ed è quella proposta).
    Alla chiusura: result = None (annullato), "tutti" oppure la lista degli id scelti;
    scelta = ciò che va ripassato come scelta_iniziale per riproporre la stessa scelta.
    """

    def __init__(self, parent, conti, titolo, scelta_iniziale=None, solo_economici=False):
        super().__init__(parent)
        self.result = None
        self.scelta = None
        self._solo_economici = solo_economici
        self._conti = list(conti)
        self._figli = {}
        for c in self._conti:
            if c["padre_id"]:
                self._figli.setdefault(c["padre_id"], []).append(c["id"])
        self._spuntati = set()
        self._modo_var = tk.StringVar(value="economici" if solo_economici else "tutti")
        if scelta_iniziale in ("tutti", "economici"):
            self._modo_var.set(scelta_iniziale)
        elif scelta_iniziale:
            esistenti = {c["id"] for c in self._conti}
            self._spuntati = set(scelta_iniziale) & esistenti
            if self._spuntati:
                self._modo_var.set("spuntati")

        self.title(titolo)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui(titolo)
        self._popola()
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self, titolo):
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"{titolo}: quali conti?", font=("", 10, "bold")).pack(anchor=tk.W)
        if self._solo_economici:
            ttk.Radiobutton(
                frame, variable=self._modo_var, value="economici", text="Solo i conti di costo e ricavo",
            ).pack(anchor=tk.W, pady=(8, 1))
        ttk.Radiobutton(
            frame, variable=self._modo_var, value="tutti", text="Tutti i conti",
        ).pack(anchor=tk.W, pady=(1 if self._solo_economici else 8, 1))
        ttk.Radiobutton(
            frame, variable=self._modo_var, value="spuntati", text="Solo i conti spuntati nell'elenco:",
        ).pack(anchor=tk.W, pady=1)

        # Intervallo di codici
        intervallo = ttk.Frame(frame)
        intervallo.pack(fill=tk.X, pady=(6, 2))
        ttk.Label(intervallo, text="Codici da").pack(side=tk.LEFT)
        self._da_var = tk.StringVar()
        self._a_var = tk.StringVar()
        da_entry = ttk.Entry(intervallo, textvariable=self._da_var, width=8)
        da_entry.pack(side=tk.LEFT, padx=4)
        ttk.Label(intervallo, text="a").pack(side=tk.LEFT)
        a_entry = ttk.Entry(intervallo, textvariable=self._a_var, width=8)
        a_entry.pack(side=tk.LEFT, padx=4)
        ttk.Button(intervallo, text="Spunta intervallo", command=self._spunta_intervallo).pack(side=tk.LEFT, padx=4)
        for entry in (da_entry, a_entry):
            entry.bind("<Return>", lambda e: (self._spunta_intervallo(), "break")[1])

        # Ricerca per codice o nome
        ricerca = ttk.Frame(frame)
        ricerca.pack(fill=tk.X, pady=2)
        ttk.Label(ricerca, text="Cerca").pack(side=tk.LEFT)
        self._cerca_var = tk.StringVar()
        self._cerca_var.trace_add("write", lambda *a: self._popola())
        cerca_entry = ttk.Entry(ricerca, textvariable=self._cerca_var, width=28)
        cerca_entry.pack(side=tk.LEFT, padx=4)
        cerca_entry.bind("<Return>", lambda e: "break")
        ttk.Label(ricerca, text="(codice o nome)", foreground="#555555").pack(side=tk.LEFT)

        # Elenco con le spunte
        lista = ttk.Frame(frame)
        lista.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        cols = ("spunta", "codice", "nome", "tipo")
        self.tree = ttk.Treeview(lista, columns=cols, show="headings", height=12, selectmode="browse")
        self.tree.heading("spunta", text="")
        self.tree.heading("codice", text="Codice")
        self.tree.heading("nome", text="Conto")
        self.tree.heading("tipo", text="Tipo")
        self.tree.column("spunta", width=30, anchor=tk.CENTER, stretch=False)
        self.tree.column("codice", width=70, anchor=tk.CENTER, stretch=False)
        self.tree.column("nome", width=260)
        self.tree.column("tipo", width=80, anchor=tk.CENTER, stretch=False)
        scrollbar = ttk.Scrollbar(lista, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Button-1>", self._on_clic)
        self.tree.bind("<space>", lambda e: self._alterna(self.tree.focus()))
        self.tree.bind("<Return>", lambda e: self._on_ok())

        comandi = ttk.Frame(frame)
        comandi.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(comandi, text="Spunta tutti quelli in elenco", command=self._spunta_visibili).pack(side=tk.LEFT)
        ttk.Button(comandi, text="Togli tutte le spunte", command=self._togli_tutti).pack(side=tk.LEFT, padx=4)
        self._conteggio = ttk.Label(comandi, foreground="#555555")
        self._conteggio.pack(side=tk.RIGHT)

        ttk.Label(
            frame,
            text="Clic su un conto (o barra spaziatrice) per spuntarlo o togliere la spunta.\n"
                 "Spuntando un conto padre si spuntano anche i suoi sottoconti.",
            foreground="#555555",
        ).pack(anchor=tk.W, pady=(8, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(12, 0))
        btn_ok = ttk.Button(btn_frame, text="Esporta...", command=self._on_ok)
        btn_ok.pack(side=tk.LEFT, padx=5)
        btn_ok.bind("<Return>", lambda e: self._on_ok())
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=5)
        btn_ok.focus_set()

    def _popola(self):
        """Riempie l'elenco con i conti che corrispondono alla ricerca."""
        testo = self._cerca_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        for c in self._conti:
            if testo and testo not in c["codice"].lower() and testo not in c["nome"].lower():
                continue
            nome = ("    " + c["nome"]) if c["padre_id"] else c["nome"]
            self.tree.insert("", tk.END, iid=str(c["id"]),
                             values=(self._segno(c["id"]), c["codice"], nome, c["tipo"]))
        self._aggiorna_conteggio()

    def _segno(self, conto_id):
        return "☑" if conto_id in self._spuntati else "☐"

    def _aggiorna(self, ids):
        for conto_id in ids:
            if self.tree.exists(str(conto_id)):
                self.tree.set(str(conto_id), "spunta", self._segno(conto_id))
        if self._spuntati:
            self._modo_var.set("spuntati")
        self._aggiorna_conteggio()

    def _aggiorna_conteggio(self):
        n = len(self._spuntati)
        self._conteggio.config(text="Nessun conto spuntato" if not n else
                               "1 conto spuntato" if n == 1 else f"{n} conti spuntati")

    def _on_clic(self, event):
        riga = self.tree.identify_row(event.y)
        if riga and self.tree.identify_region(event.x, event.y) == "cell":
            self.tree.focus(riga)
            self.tree.selection_set(riga)
            self._alterna(riga)
            self.tree.focus_set()
            return "break"

    def _alterna(self, riga):
        """Spunta o toglie la spunta a un conto (e ai suoi sottoconti)."""
        if not riga:
            return
        conto_id = int(riga)
        ids = [conto_id] + self._figli.get(conto_id, [])
        if conto_id in self._spuntati:
            self._spuntati.difference_update(ids)
        else:
            self._spuntati.update(ids)
        self._aggiorna(ids)

    def _spunta_intervallo(self):
        da = self._da_var.get().strip()
        a = self._a_var.get().strip()
        if not da and not a:
            messagebox.showwarning("Attenzione", "Indicare il codice iniziale e/o finale.", parent=self)
            return
        ids = [
            c["id"] for c in self._conti
            if (not da or chiave_codice(c["codice"]) >= chiave_codice(da))
            and (not a or chiave_codice(c["codice"]) <= chiave_codice(a))
        ]
        if not ids:
            messagebox.showinfo("Intervallo", "Nessun conto in questo intervallo di codici.", parent=self)
            return
        self._spuntati.update(ids)
        self._aggiorna(ids)

    def _spunta_visibili(self):
        ids = [int(i) for i in self.tree.get_children()]
        self._spuntati.update(ids)
        self._aggiorna(ids)

    def _togli_tutti(self):
        ids = list(self._spuntati)
        self._spuntati.clear()
        self._aggiorna(ids)

    def _on_ok(self):
        modo = self._modo_var.get()
        ordine = [c["id"] for c in self._conti]
        if modo == "tutti":
            self.result = self.scelta = "tutti"
        elif modo == "economici":
            self.scelta = "economici"
            self.result = [c["id"] for c in self._conti if c["tipo"] in ("COSTO", "RICAVO")]
        elif not self._spuntati:
            messagebox.showwarning("Attenzione", "Spuntare almeno un conto, oppure scegliere un'altra opzione.", parent=self)
            return
        else:
            self.result = [i for i in ordine if i in self._spuntati]
            self.scelta = self.result
        self.destroy()


class RiportoSaldiDialog(tk.Toplevel):
    """
    Riporto dei saldi di attivo e passivo di un esercizio all'inizio del successivo.
    Mostra i saldi che verranno registrati e chiede il conto di patrimonio netto
    da usare come contropartita (esistente oppure nuovo).
    Alla chiusura: result = numero di registrazioni create (None se annullato).
    """

    _NUOVO = "(crea un nuovo conto)"

    def __init__(self, parent, db, esercizio_id, da_esercizio_id):
        super().__init__(parent)
        self.db = db
        self.result = None
        self._esercizio = db.get_esercizio(esercizio_id)
        self._precedente = db.get_esercizio(da_esercizio_id)

        self.title("Riporta saldi di apertura")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _conti_patrimonio(self):
        """Conti di tipo PASSIVO: tra questi si sceglie il patrimonio netto."""
        return [c for c in self.db.get_conti() if c["tipo"] == "PASSIVO"]

    def _build_ui(self):
        prec, es = self._precedente, self._esercizio
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Riporto dei saldi di attivo e passivo", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(
            frame,
            text=f"Dall'esercizio: {prec['descrizione']} ({periodo_label(prec['data_inizio'], prec['data_fine'])})"
                 f"{'' if prec['data_chiusura'] else '  - ancora aperto'}\n"
                 f"All'esercizio:   {es['descrizione']}, registrazioni al {format_display(es['data_inizio'])}",
        ).pack(anchor=tk.W, pady=(6, 8))

        # Conto di patrimonio netto (contropartita)
        contro = ttk.LabelFrame(frame, text="Contropartita: conto di patrimonio netto", padding=8)
        contro.pack(fill=tk.X)
        self._labels = {f"{c['codice']} - {c['nome']}": c["id"] for c in self._conti_patrimonio()}
        valori = list(self._labels) + [self._NUOVO]
        self._contro_cb = ttk.Combobox(contro, values=valori, state="readonly", width=40)
        self._contro_cb.grid(row=0, column=0, columnspan=4, sticky=tk.W)
        proposto = next((l for l in self._labels if any(
            p in l.lower() for p in ("patrimonio", "capitale", "netto", "apertura"))), self._NUOVO)
        self._contro_cb.set(proposto)
        self._contro_cb.bind("<<ComboboxSelected>>", lambda e: self._aggiorna())

        self._nuovo_frame = ttk.Frame(contro)
        self._nuovo_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(6, 0))
        ttk.Label(self._nuovo_frame, text="Codice").pack(side=tk.LEFT)
        codici = {c["codice"] for c in self.db.get_conti()}
        codice = next((c for c in ("290", "250", "280", "299", "900") if c not in codici), "")
        self._codice_var = tk.StringVar(value=codice)
        ttk.Entry(self._nuovo_frame, textvariable=self._codice_var, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Label(self._nuovo_frame, text="Nome").pack(side=tk.LEFT)
        self._nome_var = tk.StringVar(value="Patrimonio netto")
        ttk.Entry(self._nuovo_frame, textvariable=self._nome_var, width=24).pack(side=tk.LEFT, padx=4)
        ttk.Label(self._nuovo_frame, text="(tipo PASSIVO)", foreground="#555555").pack(side=tk.LEFT)

        # Anteprima
        lista = ttk.Frame(frame)
        lista.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        cols = ("codice", "nome", "dare", "avere")
        self.tree = ttk.Treeview(lista, columns=cols, show="headings", height=9)
        for col, titolo, w, anchor in (("codice", "Codice", 70, tk.CENTER), ("nome", "Conto", 230, tk.W),
                                       ("dare", "In Dare", 100, tk.E), ("avere", "In Avere", 100, tk.E)):
            self.tree.heading(col, text=titolo)
            self.tree.column(col, width=w, anchor=anchor)
        scrollbar = ttk.Scrollbar(lista, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._riepilogo = ttk.Label(frame, foreground="#555555", justify=tk.LEFT)
        self._riepilogo.pack(anchor=tk.W, pady=(6, 0))

        gia_fatte = self.db.conta_aperture(es["id"])
        if gia_fatte:
            ttk.Label(
                frame,
                text=f"Attenzione: in questo esercizio ci sono già {gia_fatte} registrazioni \"Saldo di apertura\".\n"
                     "Riportando di nuovo, i saldi verrebbero contati due volte.",
                foreground="#b00020",
            ).pack(anchor=tk.W, pady=(6, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(12, 0))
        self._btn_ok = ttk.Button(btn_frame, text="Registra apertura", command=self._on_registra)
        self._btn_ok.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Non ora", command=self.destroy).pack(side=tk.LEFT, padx=5)
        self._aggiorna()

    def _contropartita_id(self):
        return self._labels.get(self._contro_cb.get())

    def _aggiorna(self):
        """Anteprima dei saldi da riportare con la contropartita scelta."""
        if self._contro_cb.get() == self._NUOVO:
            self._nuovo_frame.grid()
        else:
            self._nuovo_frame.grid_remove()
        self.tree.delete(*self.tree.get_children())
        righe = self.db.saldi_da_riportare(self._precedente["id"], self._contropartita_id())
        tot_dare = sum(d for _c, d, _a in righe)
        tot_avere = sum(a for _c, _d, a in righe)
        for conto, dare, avere in righe:
            nome = ("    " + conto["nome"]) if conto["padre_id"] else conto["nome"]
            self.tree.insert("", tk.END, values=(conto["codice"], nome, format_importo(dare), format_importo(avere)))
        netto = tot_dare - tot_avere
        if not righe:
            testo = "Nessun saldo da riportare: i conti di attivo e passivo sono a zero."
        else:
            testo = (f"{len(righe)} registrazioni. Attività {format_importo(tot_dare) or '0,00'}, "
                     f"passività {format_importo(tot_avere) or '0,00'}.\n"
                     f"Il patrimonio netto riceve la differenza: {format_importo(abs(netto)) or '0,00'} "
                     f"in {'Avere' if netto >= 0 else 'Dare'}.")
        self._riepilogo.config(text=testo)
        self._btn_ok.config(state=tk.NORMAL if righe else tk.DISABLED)

    def _on_registra(self):
        contropartita_id = self._contropartita_id()
        if self._contro_cb.get() == self._NUOVO:
            codice = self._codice_var.get().strip()
            nome = self._nome_var.get().strip()
            if not codice or not nome:
                messagebox.showerror("Errore", "Indicare codice e nome del nuovo conto.", parent=self)
                return
            try:
                contropartita_id = self.db.crea_conto(codice, nome, "PASSIVO")
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile creare il conto:\n{e}", parent=self)
                return
        try:
            self.result = self.db.registra_apertura(self._esercizio["id"], self._precedente["id"], contropartita_id)
        except ValueError as e:
            messagebox.showerror("Errore", str(e), parent=self)
            return
        self.destroy()
