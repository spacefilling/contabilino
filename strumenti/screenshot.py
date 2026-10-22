"""
Contabilino - Screenshot automatici delle finestre principali (solo Windows).

Apre il programma sul database di esempio, attraversa le schermate e salva
le immagini nella cartella indicata. Serve per controllare l'aspetto su
Windows (anche con lo zoom: CONTABILINO_ZOOM=150) e per la documentazione.

    pip install -r requirements.txt pillow
    python strumenti/screenshot.py cartella-di-uscita

Lo usa il workflow .github/workflows/screenshot.yml.
"""

import ctypes
import os
import shutil
import sys
import tempfile
import tkinter as tk

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import tema  # noqa: E402
from db import Database  # noqa: E402

USCITA = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "screenshot")
os.makedirs(USCITA, exist_ok=True)
controlli = []  # (descrizione, esito)


def rettangolo(finestra):
    """Rettangolo della finestra sullo schermo, bordi e barra del titolo compresi."""
    finestra.update()
    hwnd = int(finestra.wm_frame(), 16)
    rect = ctypes.wintypes.RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
    )
    return rect.left, rect.top, rect.right, rect.bottom


def foto(finestra, nome, extra=None):
    """Salva l'immagine della finestra (e di un'altra finestra sovrapposta, es. la tendina)."""
    from PIL import ImageGrab
    finestra.update()
    finestra.after(400)
    finestra.update()
    x1, y1, x2, y2 = rettangolo(finestra)
    if extra is not None:
        ex = extra.winfo_rootx(), extra.winfo_rooty()
        x2 = max(x2, ex[0] + extra.winfo_width() + 8)
        y2 = max(y2, ex[1] + extra.winfo_height() + 8)
    ImageGrab.grab(bbox=(x1, y1, x2, y2), all_screens=True).save(os.path.join(USCITA, nome + ".png"))
    print("salvato", nome)


def main():
    import ctypes.wintypes  # noqa: F401  (serve a rettangolo)

    tema.abilita_dpi()
    cartella = tempfile.mkdtemp()
    percorso = os.path.join(cartella, "contabilino.db")
    shutil.copy(os.path.join(RADICE, "esempi", "contabilino-esempio.db"), percorso)
    db = Database(percorso)
    db.connect()
    db.create_tables()
    nuovo = db.crea_esercizio("Esercizio 2027", "2027-01-01", "2027-12-31")  # per il riporto dei saldi
    db.chiudi_esercizio(db.get_esercizio_precedente(nuovo)["id"], "2026-12-31")
    vecchio = db.get_esercizio_precedente(nuovo)["id"]

    import dialogs
    from export import conti_economici
    from ui import MainWindow

    root = tk.Tk()
    tema.applica(root)
    w = MainWindow(root, db)
    root.geometry("+40+40")
    w._set_esercizio(vecchio)
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()

    # 1. Libro giornale con una registrazione selezionata
    righe = w.giornale_tree.get_children()
    w.giornale_tree.selection_set(righe[5])
    w._aggiorna_azioni()
    foto(root, "01-libro-giornale")

    # 2. Tendina dei conti mentre si scrive nel Conto Dare
    w._input_data.set_iso_date("2026-12-15")
    w._input_causale.set_value("Fattura Molino Valle Verde")
    w._input_dare.focus_force()
    w._input_dare._var.set("40")
    w._input_dare._update_popup()
    foto(root, "02-tendina-conti", extra=w._input_dare._popup)

    # 3. Clic su un altro campo: la tendina deve chiudersi
    w._input_importo.focus_force()
    root.update()
    root.after(300)
    root.update()
    controlli.append(("tendina chiusa passando al campo Importo", w._input_dare._popup is None))
    w._input_dare._update_popup()
    root.update()
    w.giornale_tree.event_generate("<ButtonPress-1>", x=40, y=40)
    root.update()
    controlli.append(("tendina chiusa con un clic sulla tabella", w._input_dare._popup is None))
    w._clear_input_row()

    # 4. Saldi conti
    w.notebook.select(1)
    foto(root, "03-saldi-conti")
    w.notebook.select(0)

    # 5. Dialoghi
    def dialogo(crea, nome):
        finestra = crea()
        finestra.attributes("-topmost", True)
        foto(finestra, nome)
        finestra.destroy()

    dialogo(lambda: dialogs.SelezioneContiDialog(root, db.get_conti(), "Partitari", None, solo_economici=True),
            "04-scelta-conti")
    dialogo(lambda: dialogs.RiportoSaldiDialog(root, db, nuovo, vecchio), "05-riporto-saldi")
    dialogo(lambda: dialogs.GestioneContiDialog(root, db), "06-piano-dei-conti")
    dialogo(lambda: dialogs.GestioneEserciziDialog(root, db, vecchio), "07-esercizi")

    # 6. Schermo intero: barra delle applicazioni con l'icona
    from PIL import ImageGrab
    ImageGrab.grab(all_screens=True).save(os.path.join(USCITA, "08-schermo-intero.png"))

    root.destroy()
    with open(os.path.join(USCITA, "controlli.txt"), "w", encoding="utf-8") as f:
        for descrizione, esito in controlli:
            riga = f"{'OK  ' if esito else 'ERRORE'}  {descrizione}"
            print(riga)
            f.write(riga + "\n")
    if not all(esito for _d, esito in controlli):
        sys.exit(1)


if __name__ == "__main__":
    main()
