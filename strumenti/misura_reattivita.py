"""
Contabilino - Misura dei tempi di risposta dell'interfaccia.

Simula i clic più comuni (riga del giornale, cambio scheda, campi della riga
di inserimento, pulsanti) e misura quanto impiega Tk a gestirli e ridisegnare.
Con TEMA=classico usa l'aspetto standard di Tk, per il confronto.

    python strumenti/misura_reattivita.py
"""

import os
import shutil
import statistics
import sys
import tempfile
import time
import tkinter as tk

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import tema  # noqa: E402
from db import Database  # noqa: E402


def cronometra(root, azione, ripetizioni=15):
    tempi = []
    for _ in range(ripetizioni):
        root.update()
        inizio = time.perf_counter()
        azione()
        root.update()
        tempi.append((time.perf_counter() - inizio) * 1000)
    return statistics.median(tempi), max(tempi)


def main():
    tema.abilita_dpi()
    cartella = tempfile.mkdtemp()
    percorso = os.path.join(cartella, "contabilino.db")
    shutil.copy(os.path.join(RADICE, "esempi", "contabilino-esempio.db"), percorso)
    db = Database(percorso)
    db.connect()
    db.create_tables()

    from ui import MainWindow
    root = tk.Tk()
    if os.environ.get("TEMA") != "classico":
        tema.applica(root)
    w = MainWindow(root, db)
    root.update()

    righe = w.giornale_tree.get_children()
    prove = {
        "clic su una riga del giornale": lambda: w.giornale_tree.event_generate(
            "<ButtonPress-1>", x=200, y=w.giornale_tree.bbox(righe[3])[1] + 5) or
            w.giornale_tree.event_generate("<ButtonRelease-1>", x=200, y=w.giornale_tree.bbox(righe[3])[1] + 5),
        "selezione di una riga": lambda: w.giornale_tree.selection_set(righe[len(righe) // 2]),
        "cambio scheda (Saldi e ritorno)": lambda: (w.notebook.select(1), root.update(), w.notebook.select(0)),
        "clic nel campo Causale": lambda: (w._input_causale.focus_force(), root.update(), w._input_data.focus_force()),
        "clic nel campo Conto Dare (tendina)": lambda: (w._input_dare.focus_force(), root.update(), w._input_data.focus_force()),
        "passaggio del mouse sui pulsanti": lambda: [b.event_generate("<Enter>") or b.event_generate("<Leave>")
                                                     for b in (w._btn_modifica, w._btn_elimina, w._btn_storno)],
        "aggiornamento del giornale": w._refresh_giornale,
    }
    print(f"Tema: {os.environ.get('TEMA', 'Contabilino')} | registrazioni: {len(righe)}")
    for nome, azione in prove.items():
        mediana, massimo = cronometra(root, azione)
        print(f"  {nome:40s} mediana {mediana:7.1f} ms   max {massimo:7.1f} ms")
    root.destroy()


if __name__ == "__main__":
    main()
