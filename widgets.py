"""
Contabilino - Widget personalizzati
SmartDateEntry: input data con auto-formattazione (20260212 → 12/02/2026)
AmountEntry: input importo stile registratore di cassa (10000 → 100,00)
AutocompleteEntry: input con ricerca e dropdown filtrato
format_importo: importo in stile italiano (1234.56 → 1.234,56)
"""

import tkinter as tk
from tkinter import ttk

from dateutils import to_iso, format_display


def format_importo(amount):
    """Formatta importo in stile italiano: 1.234,56"""
    amount = round(amount, 2) + 0.0  # evita "-0,00" dagli arrotondamenti dei decimali
    if amount == 0:
        return ""
    s = f"{amount:,.2f}"
    # Swap . and , for Italian format
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


class SmartDateEntry(ttk.Entry):
    """
    Campo data che accetta formati compatti.
    Digitare 20260212 e al Tab/Enter diventa 12/02/2026.
    Accetta anche 12022026, 12/02/2026 o 1/7/2026 (normalizzato in 01/07/2026).
    """

    def __init__(self, master, on_change=None, **kwargs):
        self._var = tk.StringVar()
        super().__init__(master, textvariable=self._var, **kwargs)
        self._on_change = on_change
        self.bind("<FocusOut>", self._format)
        self.bind("<Return>", self._on_return)

    def _format(self, event=None):
        raw = self._var.get().strip()
        if not raw:
            return
        iso = to_iso(raw)
        if iso:
            self._var.set(format_display(iso))
        if self._on_change:
            self._on_change()

    def _on_return(self, event=None):
        self._format()
        # Sposta al prossimo widget
        next_widget = self.tk_focusNext()
        if next_widget:
            next_widget.focus_set()
        return "break"

    def get_iso_date(self):
        """Restituisce la data in formato ISO (AAAA-MM-GG), '' se non valida."""
        return to_iso(self._var.get())

    def set_iso_date(self, iso_date):
        """Imposta il campo a partire da una data ISO."""
        self._var.set(format_display(iso_date))

    def is_empty(self):
        return not self._var.get().strip()

    def clear(self):
        self._var.set("")


def centesimi_da_testo(testo):
    """
    Importo scritto per esteso → centesimi (None se non è un importo).
    Con la virgola è in stile italiano (1.250,50); senza, un punto seguito
    da tre cifre è il separatore delle migliaia (1.250), altrimenti i decimali (1250.5).
    """
    s = "".join(ch for ch in str(testo) if ch.isdigit() or ch in ",.")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3):
        s = s.replace(".", "")
    try:
        valore = float(s)
    except ValueError:
        return None
    return int(round(valore * 100))


class AmountEntry(ttk.Entry):
    """
    Campo importo stile registratore di cassa.
    Digitare 10000 per ottenere 100,00.
    Digitare 1500 per ottenere 15,00.
    Solo cifre accettate, la virgola è inserita automaticamente.
    """

    def __init__(self, master, **kwargs):
        self._var = tk.StringVar()
        kwargs.pop("textvariable", None)
        super().__init__(master, textvariable=self._var, **kwargs)
        self._cents = 0
        self.bind("<Key>", self._on_key)
        # Incolla e taglia devono aggiornare anche l'importo, non solo il testo mostrato
        self.bind("<<Paste>>", self._on_paste)
        self.bind("<<PasteSelection>>", lambda e: "break")
        self.bind("<<Cut>>", self._on_cut)
        self.bind("<<Clear>>", lambda e: (self.set_amount(0), "break")[1])

    def _on_key(self, event):
        if event.char and event.char.isdigit():
            self._cents = self._cents * 10 + int(event.char)
            self._update_display()
            return "break"
        elif event.keysym == "BackSpace":
            self._cents = self._cents // 10
            self._update_display()
            return "break"
        elif event.keysym in ("Tab", "Return", "Escape", "Shift_L", "Shift_R"):
            return  # Lascia propagare
        elif event.keysym == "Delete":
            self._cents = 0
            self._update_display()
            return "break"
        elif event.state & 0x4:
            # Ctrl+qualcosa: lascia passare (Ctrl+C, Ctrl+A, ecc.)
            return
        return "break"

    def _on_paste(self, event=None):
        """Incolla un importo scritto per esteso: 1250  1250,5  1.250,00  1250.00"""
        try:
            testo = self.clipboard_get()
        except tk.TclError:
            return "break"
        cents = centesimi_da_testo(testo)
        if cents is not None:
            self._cents = cents
            self._update_display()
            self.icursor(tk.END)
        return "break"

    def _on_cut(self, event=None):
        """Taglia: l'importo va negli appunti e il campo torna a zero."""
        if self._var.get():
            self.clipboard_clear()
            self.clipboard_append(self._var.get())
        self._cents = 0
        self._update_display()
        return "break"

    def _update_display(self):
        if self._cents == 0:
            self._var.set("0,00")
        else:
            euros = self._cents // 100
            cents = self._cents % 100
            self._var.set(f"{euros},{cents:02d}")

    def get_amount(self):
        """Restituisce l'importo come float."""
        return self._cents / 100.0

    def set_amount(self, amount):
        """Imposta l'importo (float), es. per correggere una registrazione."""
        self._cents = int(round(amount * 100))
        self._update_display()

    def clear(self):
        self._cents = 0
        self._var.set("")


class AutocompleteEntry(ttk.Entry):
    """
    Campo con autocompletamento a dropdown.
    Digitare per filtrare, frecce per navigare, Enter/Tab per selezionare.
    """

    def __init__(self, master, values=None, allow_free_text=False, **kwargs):
        self._var = tk.StringVar()
        super().__init__(master, textvariable=self._var, **kwargs)
        self._all_values = list(values) if values else []
        self._allow_free_text = allow_free_text
        self._popup = None
        self._listbox = None
        self._ignore_focus_out = False

        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<Return>", self._on_return)
        self.bind("<Tab>", self._on_tab)
        self.bind("<Escape>", self._close_popup)
        self.bind("<Down>", self._on_arrow_down)
        self.bind("<Up>", self._on_arrow_up)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<FocusIn>", self._on_focus_in)

    def set_values(self, values):
        """Aggiorna la lista dei valori disponibili."""
        self._all_values = list(values)

    def set_value(self, value):
        """Imposta il testo senza aprire il dropdown."""
        self._var.set(value)
        self.icursor(tk.END)
        self._close_popup()

    def _get_matches(self):
        typed = self._var.get().strip().lower()
        if not typed:
            return self._all_values[:15]  # Mostra i primi 15 se vuoto
        return [v for v in self._all_values if typed in v.lower()]

    def _on_focus_in(self, event=None):
        # Mostra dropdown se c'è testo o se non è free text
        if self._var.get().strip() or not self._allow_free_text:
            self._update_popup()

    def _on_key_release(self, event):
        if event.keysym in ("Return", "Tab", "Escape", "Up", "Down",
                            "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return
        self._update_popup()

    def _update_popup(self):
        matches = self._get_matches()
        if not matches:
            self._close_popup()
            return

        if self._popup is None:
            self._create_popup()

        self._listbox.delete(0, tk.END)
        for m in matches:
            self._listbox.insert(tk.END, m)

        # Seleziona la voce identica al testo scritto (così Tab non la sostituisce
        # con una voce più lunga che la contiene), altrimenti la prima
        typed = self._var.get().strip().lower()
        idx = next((i for i, m in enumerate(matches) if m.lower() == typed), 0)
        if self._listbox.size() > 0:
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(idx)
            self._listbox.see(idx)

        # Ridimensiona altezza
        num_items = min(self._listbox.size(), 8)
        self._listbox.configure(height=num_items)
        self._position_popup()

    def _create_popup(self):
        self._popup = tk.Toplevel(self)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_attributes("-topmost", True)

        self._listbox = tk.Listbox(
            self._popup,
            font=self.cget("font") if self.cget("font") else None,
            selectmode=tk.SINGLE,
            activestyle="none",
            exportselection=False,
        )
        self._listbox.pack(fill=tk.BOTH, expand=True)
        self._listbox.bind("<Button-1>", self._on_listbox_click)
        self._listbox.bind("<Double-Button-1>", self._on_listbox_double_click)

    def _position_popup(self):
        if self._popup is None:
            return
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = max(self.winfo_width(), 200)
        h = self._listbox.winfo_reqheight() + 4
        self._popup.geometry(f"{w}x{h}+{x}+{y}")

    def _close_popup(self, event=None):
        if self._popup:
            self._popup.destroy()
            self._popup = None
            self._listbox = None

    def _select_current(self):
        """Seleziona l'elemento corrente dal dropdown."""
        if self._listbox and self._listbox.curselection():
            value = self._listbox.get(self._listbox.curselection()[0])
            self._var.set(value)
            self.icursor(tk.END)
        elif not self._allow_free_text:
            # Se non è free text, prova a completare con il primo match
            matches = self._get_matches()
            if matches:
                self._var.set(matches[0])
                self.icursor(tk.END)
        self._close_popup()

    def _on_return(self, event):
        if self._popup:
            self._select_current()
            # Sposta al prossimo widget
            next_widget = self.tk_focusNext()
            if next_widget:
                next_widget.focus_set()
            return "break"
        return  # Lascia propagare se popup non aperto

    def _on_tab(self, event):
        if self._popup:
            self._select_current()
        return  # Non fare break: Tab deve propagare

    def _on_focus_out(self, event):
        # Ritardo per permettere click sulla listbox
        self.after(150, self._delayed_focus_out)

    def _delayed_focus_out(self):
        if self._popup and not self.focus_get():
            self._close_popup()

    def _on_arrow_down(self, event):
        if self._listbox:
            sel = self._listbox.curselection()
            if sel:
                idx = sel[0] + 1
                if idx < self._listbox.size():
                    self._listbox.selection_clear(0, tk.END)
                    self._listbox.selection_set(idx)
                    self._listbox.see(idx)
            elif self._listbox.size() > 0:
                self._listbox.selection_set(0)
                self._listbox.see(0)
            return "break"
        else:
            self._update_popup()
            return "break"

    def _on_arrow_up(self, event):
        if self._listbox:
            sel = self._listbox.curselection()
            if sel:
                idx = sel[0] - 1
                if idx >= 0:
                    self._listbox.selection_clear(0, tk.END)
                    self._listbox.selection_set(idx)
                    self._listbox.see(idx)
            return "break"

    def _on_listbox_click(self, event):
        self._ignore_focus_out = True
        self.after(200, self._reset_ignore)

    def _on_listbox_double_click(self, event):
        self._select_current()
        self.focus_set()

    def _reset_ignore(self):
        if self._listbox and self._listbox.curselection():
            value = self._listbox.get(self._listbox.curselection()[0])
            self._var.set(value)
            self.icursor(tk.END)
        self._close_popup()
        self._ignore_focus_out = False
        # Sposta al prossimo widget
        next_widget = self.tk_focusNext()
        if next_widget:
            next_widget.focus_set()

    def get_value(self):
        return self._var.get().strip()

    def clear(self):
        self._var.set("")
        self._close_popup()
