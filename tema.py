"""
Contabilino - Aspetto grafico
Stile Windows 11 (Fluent) disegnato sul tema "clam" di Tk: solo colori e
linee, niente immagini, così l'interfaccia resta veloce. Testo nitido con lo
zoom di Windows (125%, 150%...), icona della finestra e misure in pixel adattate.

Uso:
    tema.abilita_dpi()          prima di creare la prima finestra Tk
    tema.applica(root)          subito dopo aver creato la finestra principale
    tema.px(120)                una misura in pixel pensata per lo zoom al 100%
"""

import os
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from icona import ICONE, SPUNTE

SCALA = 1.0  # rapporto tra i DPI dello schermo e 96 (zoom di Windows al 100%)

# Colori del tema chiaro (Fluent / Windows 11)
SFONDO = "#f7f7f7"
SFONDO_CARD = "#ffffff"
SFONDO_HOVER = "#f2f2f2"
SFONDO_PREMUTO = "#e9e9e9"
TESTO = "#1c1c1c"
TESTO_SECONDARIO = "#616161"
TESTO_DISATTIVO = "#a0a0a0"
BORDO = "#e5e5e5"
BORDO_CONTROLLO = "#d1d1d1"
ACCENTO = "#005fb8"
ACCENTO_HOVER = "#1a6fc0"
ACCENTO_PREMUTO = "#004c94"
SELEZIONE_LISTA = "#e3ecf7"
ERRORE = "#c42b1c"

# Font con nome, definiti in applica(): si usano come font="Contabilino.Titolo"
FONT_TITOLO = "Contabilino.Titolo"
FONT_SOTTOTITOLO = "Contabilino.Sottotitolo"
FONT_TESTO = "Contabilino.Testo"
FONT_FORTE = "Contabilino.Forte"
FONT_PICCOLO = "Contabilino.Piccolo"

_icone = []  # riferimenti alle immagini: Tk le perde se Python le libera
_font = []  # idem per i font creati da Python
ICONA_DA_ICO = False  # True quando l'icona della finestra viene dal file .ico (Windows)


def abilita_dpi():
    """
    Su Windows dichiara il programma "consapevole dei DPI": il testo viene
    disegnato alla risoluzione vera dello schermo invece di essere ingrandito
    (e sfocato) da Windows. Va chiamata prima di creare la prima finestra.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Windows 8.1 e successivi
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()  # Windows Vista/7
    except Exception:
        pass  # al peggio il testo resta un po' sfocato, il programma funziona
    try:
        # Barra delle applicazioni: raggruppa le finestre come "Contabilino", con il suo logo
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("spacefilling.Contabilino")
    except Exception:
        pass


def px(valore):
    """Misura in pixel (pensata a zoom 100%) adattata allo zoom dello schermo."""
    return int(round(valore * SCALA))


def applica(root):
    """Tema, font, icona e stili di Contabilino sulla finestra principale."""
    global SCALA
    # Prova di come appare con lo zoom di Windows (es. CONTABILINO_ZOOM=150), anche al 100%
    zoom_prova = os.environ.get("CONTABILINO_ZOOM")
    if zoom_prova:
        root.tk.call("tk", "scaling", float(zoom_prova) / 100 * 96 / 72)
    if sys.platform == "win32" or zoom_prova:
        SCALA = max(1.0, root.winfo_fpixels("1i") / 96)

    _crea_font(root)
    _stili(root)
    imposta_icona(root)
    root.configure(background=SFONDO)
    # Colori di base per i widget tk classici (elenchi, menu a comparsa)
    root.option_add("*Listbox.font", FONT_TESTO)
    root.option_add("*Menu.font", FONT_TESTO)


def _famiglia(root):
    """
    Segoe UI Variable su Windows 11, Segoe UI su Windows 10; su Linux il font
    dell'interfaccia più comune disponibile; su Mac il font di sistema.
    """
    disponibili = set(tkfont.families(root))
    for famiglia in ("Segoe UI Variable Text", "Segoe UI", "Cantarell", "Ubuntu", "Noto Sans",
                     "Inter", "Liberation Sans", "DejaVu Sans"):
        if famiglia in disponibili:
            return famiglia
    return tkfont.nametofont("TkDefaultFont", root).actual("family")


def _crea_font(root):
    """Font in punti (non in pixel), così crescono con lo zoom di Windows."""
    famiglia = _famiglia(root)
    titolo = "Segoe UI Variable Display" if famiglia == "Segoe UI Variable Text" else famiglia
    definizioni = {
        FONT_TITOLO: dict(family=titolo, size=15, weight="bold"),
        FONT_SOTTOTITOLO: dict(family=titolo, size=11, weight="bold"),
        FONT_TESTO: dict(family=famiglia, size=10),
        FONT_FORTE: dict(family=famiglia, size=10, weight="bold"),
        FONT_PICCOLO: dict(family=famiglia, size=9),
    }
    for nome, opzioni in definizioni.items():
        if nome in tkfont.names(root):
            tkfont.nametofont(nome, root).configure(**opzioni)
        else:
            _font.append(tkfont.Font(root, name=nome, **opzioni))

    for nome in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(nome, root).configure(family=famiglia, size=10)


def _stili(root):
    """
    Stile Fluent sul tema "clam": elementi disegnati con colori e linee
    (i temi fatti di immagini, come Sun Valley, rallentano ogni clic).
    """
    style = ttk.Style(root)
    style.theme_use("clam")
    linea = tkfont.nametofont(FONT_TESTO, root).metrics("linespace")

    style.configure(
        ".", background=SFONDO, foreground=TESTO, font=FONT_TESTO,
        bordercolor=BORDO_CONTROLLO, lightcolor=SFONDO, darkcolor=SFONDO,
        troughcolor=SFONDO, focuscolor=SFONDO, selectbackground=SELEZIONE_LISTA,
        selectforeground=TESTO, fieldbackground=SFONDO_CARD, insertcolor=TESTO,
    )
    style.map(".", foreground=[("disabled", TESTO_DISATTIVO)])

    # Pulsanti: bianchi con bordo sottile; "Accent" blu per l'azione principale
    style.configure(
        "TButton", background=SFONDO_CARD, bordercolor=BORDO_CONTROLLO,
        lightcolor=SFONDO_CARD, darkcolor=SFONDO_CARD, padding=(px(12), px(5)),
        anchor="center", focuscolor=SFONDO_CARD,
    )
    style.map(
        "TButton",
        background=[("disabled", SFONDO), ("pressed", SFONDO_PREMUTO), ("active", SFONDO_HOVER)],
        lightcolor=[("disabled", SFONDO), ("pressed", SFONDO_PREMUTO), ("active", SFONDO_HOVER)],
        darkcolor=[("disabled", SFONDO), ("pressed", SFONDO_PREMUTO), ("active", SFONDO_HOVER)],
        bordercolor=[("disabled", BORDO), ("focus", ACCENTO)],
        focuscolor=[("pressed", SFONDO_PREMUTO), ("active", SFONDO_HOVER)],
    )
    style.configure(
        "Accent.TButton", background=ACCENTO, foreground="#ffffff", bordercolor=ACCENTO,
        lightcolor=ACCENTO, darkcolor=ACCENTO, focuscolor=ACCENTO,
    )
    style.map(
        "Accent.TButton",
        background=[("disabled", "#9fb8d6"), ("pressed", ACCENTO_PREMUTO), ("active", ACCENTO_HOVER)],
        lightcolor=[("disabled", "#9fb8d6"), ("pressed", ACCENTO_PREMUTO), ("active", ACCENTO_HOVER)],
        darkcolor=[("disabled", "#9fb8d6"), ("pressed", ACCENTO_PREMUTO), ("active", ACCENTO_HOVER)],
        bordercolor=[("disabled", "#9fb8d6"), ("pressed", ACCENTO_PREMUTO), ("active", ACCENTO_HOVER)],
        focuscolor=[("pressed", ACCENTO_PREMUTO), ("active", ACCENTO_HOVER)],
        foreground=[("disabled", "#ffffff")],
    )

    # Campi di testo e tendine: bianchi, bordo grigio, blu quando hanno il focus
    for nome in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(
            nome, fieldbackground=SFONDO_CARD, background=SFONDO_CARD,
            bordercolor=BORDO_CONTROLLO, lightcolor=SFONDO_CARD, darkcolor=SFONDO_CARD,
            padding=(px(6), px(4)), arrowcolor=TESTO_SECONDARIO, arrowsize=px(12),
        )
        style.map(
            nome,
            bordercolor=[("focus", ACCENTO)],
            lightcolor=[("focus", SFONDO_CARD)],
            fieldbackground=[("readonly", SFONDO_CARD), ("disabled", SFONDO)],
            selectbackground=[("readonly", SFONDO_CARD)],
            selectforeground=[("readonly", TESTO)],
            background=[("active", SFONDO_HOVER), ("pressed", SFONDO_PREMUTO)],
        )
    # Elenco a comparsa delle combobox
    root.option_add("*TCombobox*Listbox.background", SFONDO_CARD)
    root.option_add("*TCombobox*Listbox.foreground", TESTO)
    root.option_add("*TCombobox*Listbox.selectBackground", SELEZIONE_LISTA)
    root.option_add("*TCombobox*Listbox.selectForeground", TESTO)
    root.option_add("*TCombobox*Listbox.font", FONT_TESTO)
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    # Pulsanti radio e caselle
    for nome in ("TRadiobutton", "TCheckbutton"):
        style.configure(
            nome, background=SFONDO, indicatorbackground=SFONDO_CARD,
            indicatorforeground=SFONDO_CARD, indicatormargin=(0, 0, px(6), 0),
            focuscolor=SFONDO, padding=(0, px(2)),
        )
        style.map(
            nome,
            background=[("active", SFONDO)],
            indicatorbackground=[("selected", ACCENTO), ("active", SFONDO_HOVER)],
            indicatorforeground=[("selected", "#ffffff")],
        )

    # Schede
    style.configure("TNotebook", background=SFONDO, bordercolor=BORDO, lightcolor=SFONDO, darkcolor=SFONDO,
                    tabmargins=(0, 0, 0, 0))
    style.configure(
        "TNotebook.Tab", background=SFONDO, foreground=TESTO_SECONDARIO, bordercolor=BORDO,
        lightcolor=SFONDO, darkcolor=SFONDO, padding=(px(16), px(7)), focuscolor=SFONDO,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", SFONDO_CARD), ("active", SFONDO_HOVER)],
        lightcolor=[("selected", SFONDO_CARD)],
        foreground=[("selected", TESTO)],
        expand=[("selected", (0, 0, 0, 0))],
    )

    # Tabelle: bianche, intestazione piatta, selezione azzurra
    style.configure(
        "Treeview", background=SFONDO_CARD, fieldbackground=SFONDO_CARD, foreground=TESTO,
        bordercolor=BORDO, lightcolor=SFONDO_CARD, darkcolor=SFONDO_CARD,
        rowheight=linea + px(10), font=FONT_TESTO, indent=px(18),
    )
    style.map("Treeview", background=[("selected", SELEZIONE_LISTA)], foreground=[("selected", TESTO)])
    style.configure(
        "Treeview.Heading", background=SFONDO_CARD, foreground=TESTO_SECONDARIO, font=FONT_PICCOLO,
        bordercolor=BORDO, lightcolor=SFONDO_CARD, darkcolor=SFONDO_CARD, relief="flat",
        padding=(px(6), px(5)),
    )
    style.map("Treeview.Heading", background=[("active", SFONDO_HOVER)], lightcolor=[("active", SFONDO_HOVER)])

    # Barre di scorrimento sottili
    for nome in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(
            nome, background="#e2e2e2", troughcolor=SFONDO_CARD, bordercolor=SFONDO_CARD,
            lightcolor="#e2e2e2", darkcolor="#e2e2e2", arrowcolor=TESTO_SECONDARIO,
            arrowsize=px(12), gripcount=0,
        )
        style.map(nome, background=[("active", "#cfcfcf"), ("pressed", "#bdbdbd")],
                  lightcolor=[("active", "#cfcfcf")], darkcolor=[("active", "#cfcfcf")])

    # Riquadri e separatori
    style.configure("TLabelframe", background=SFONDO, bordercolor=BORDO, lightcolor=SFONDO, darkcolor=SFONDO,
                    relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=SFONDO, foreground=TESTO_SECONDARIO, font=FONT_PICCOLO)
    style.configure("TSeparator", background=BORDO)

    # Etichette
    style.configure("Titolo.TLabel", font=FONT_TITOLO)
    style.configure("Sottotitolo.TLabel", font=FONT_SOTTOTITOLO)
    style.configure("Forte.TLabel", font=FONT_FORTE)
    style.configure("Secondario.TLabel", font=FONT_PICCOLO, foreground=TESTO_SECONDARIO)
    style.configure("Nota.TLabel", foreground=TESTO_SECONDARIO)
    style.configure("Errore.TLabel", foreground=ERRORE)
    style.configure("Stato.TLabel", font=FONT_PICCOLO, foreground=TESTO_SECONDARIO, padding=(px(12), px(6)))


def percorso_risorsa(relativo):
    """Percorso di un file del progetto, anche dentro l'eseguibile (PyInstaller lo estrae in _MEIPASS)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relativo)


def imposta_icona(root):
    """
    Logo nella barra del titolo e nella barra delle applicazioni, per questa
    finestra e per tutte quelle che si apriranno dopo (dialoghi compresi).
    Su Windows usa il file .ico con tutte le misure (il metodo nativo, il più
    affidabile); altrove, o se il file manca, le immagini PNG incorporate.
    """
    try:
        immagini = [tk.PhotoImage(master=root, data=dati)
                    for _misura, dati in sorted(ICONE.items(), reverse=True)]
        _icone.extend(immagini)
        root.iconphoto(True, *immagini)
    except tk.TclError:
        pass
    global ICONA_DA_ICO
    ico = percorso_risorsa(os.path.join("risorse", "contabilino.ico"))
    if sys.platform == "win32" and os.path.exists(ico):
        try:
            root.iconbitmap(ico)
            root.iconbitmap(default=ico)
            ICONA_DA_ICO = True
        except tk.TclError:
            pass


def logo(root, misura=32):
    """Il logo come immagine Tk, per mostrarlo nell'interfaccia."""
    dati = ICONE.get(misura) or ICONE[max(ICONE)]
    immagine = tk.PhotoImage(master=root, data=dati)
    _icone.append(immagine)
    return immagine


def immagini_spunta(master):
    """Caselle di spunta (vuota, piena) della misura adatta allo zoom, per gli elenchi."""
    misura = min(SPUNTE, key=lambda m: abs(m - 16 * SCALA))
    immagini = tuple(tk.PhotoImage(master=master, data=dati) for dati in SPUNTE[misura])
    _icone.extend(immagini)
    return immagini
