"""
Contabilino - Aspetto grafico
Tema Sun Valley (stile Windows 11), testo nitido sugli schermi con lo zoom
di Windows (125%, 150%...), icona della finestra e misure in pixel adattate.

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
SFONDO = "#fafafa"
SFONDO_CARD = "#ffffff"
TESTO = "#1c1c1c"
TESTO_SECONDARIO = "#5f5f5f"
BORDO = "#e5e5e5"
ACCENTO = "#005fb8"
SELEZIONE_LISTA = "#e8eef8"
ERRORE = "#c42b1c"

# Font con nome, definiti in applica(): si usano come font="Contabilino.Titolo"
FONT_TITOLO = "Contabilino.Titolo"
FONT_SOTTOTITOLO = "Contabilino.Sottotitolo"
FONT_TESTO = "Contabilino.Testo"
FONT_FORTE = "Contabilino.Forte"
FONT_PICCOLO = "Contabilino.Piccolo"

_icone = []  # riferimenti alle immagini: Tk le perde se Python le libera
_font = []  # idem per i font creati da Python


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

    try:
        import sv_ttk
        sv_ttk.set_theme("light", root)
    except Exception:
        pass  # senza il tema resta l'aspetto standard di Tk

    _crea_font(root)
    _stili(root)
    _imposta_icona(root)
    root.configure(background=SFONDO)
    # Colori di base per i widget tk classici (elenchi, menu a comparsa)
    root.option_add("*Listbox.font", FONT_TESTO)
    root.option_add("*Menu.font", FONT_TESTO)


def _famiglia(root):
    """Segoe UI Variable su Windows 11, Segoe UI su Windows 10, il font di sistema altrove."""
    disponibili = set(tkfont.families(root))
    for famiglia in ("Segoe UI Variable Text", "Segoe UI"):
        if famiglia in disponibili:
            return famiglia
    return tkfont.nametofont("TkDefaultFont", root).actual("family")


def _crea_font(root):
    """
    Font in punti (non in pixel), così crescono con lo zoom di Windows.
    Anche i font del tema Sun Valley, definiti in pixel, passano in punti.
    """
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

    sun_valley = {
        "SunValleyCaptionFont": 9, "SunValleyBodyFont": 10, "SunValleyBodyStrongFont": 10,
        "SunValleyBodyLargeFont": 13, "SunValleySubtitleFont": 15, "SunValleyTitleFont": 21,
    }
    for nome, punti in sun_valley.items():
        if nome in tkfont.names(root):
            tkfont.nametofont(nome, root).configure(family=famiglia, size=punti)
    for nome in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(nome, root).configure(family=famiglia, size=10)


def _stili(root):
    style = ttk.Style(root)
    linea = tkfont.nametofont(FONT_TESTO, root).metrics("linespace")
    style.configure("Treeview", rowheight=linea + px(10), font=FONT_TESTO)
    style.configure("Treeview.Heading", font=FONT_PICCOLO)
    style.configure("Titolo.TLabel", font=FONT_TITOLO)
    style.configure("Sottotitolo.TLabel", font=FONT_SOTTOTITOLO)
    style.configure("Forte.TLabel", font=FONT_FORTE)
    style.configure("Secondario.TLabel", font=FONT_PICCOLO, foreground=TESTO_SECONDARIO)
    style.configure("Nota.TLabel", foreground=TESTO_SECONDARIO)
    style.configure("Errore.TLabel", foreground=ERRORE)
    style.configure("Stato.TLabel", font=FONT_PICCOLO, foreground=TESTO_SECONDARIO, padding=(px(12), px(6)))
    style.configure("TNotebook.Tab", padding=(px(14), px(6)))


def _imposta_icona(root):
    """Logo nella barra del titolo e nella barra delle applicazioni (anche per i dialoghi)."""
    try:
        immagini = [tk.PhotoImage(master=root, data=dati)
                    for _misura, dati in sorted(ICONE.items(), reverse=True)]
    except tk.TclError:
        return
    _icone.extend(immagini)
    root.iconphoto(True, *immagini)


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
