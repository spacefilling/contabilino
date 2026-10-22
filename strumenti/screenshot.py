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
    import avvio

    # 0. Finestra di benvenuto: con un archivio trovato nella cartella e con la cartella vuota
    cartella_avvio = tempfile.mkdtemp()
    shutil.copy(percorso, os.path.join(cartella_avvio, "contabilita-2026.db"))
    for nome, archivi in (("00-benvenuto", avvio.archivi_nella_cartella(cartella_avvio)), ("00-benvenuto-vuoto", [])):
        finestra = avvio.FinestraAvvio(cartella_avvio, archivi)
        finestra.root.attributes("-topmost", True)
        foto(finestra.root, nome)
        finestra.root.destroy()
    controlli.append(("benvenuto: archivio rinominato trovato", len(avvio.archivi_nella_cartella(cartella_avvio)) == 1))

    root = tk.Tk()
    tema.applica(root)
    w = MainWindow(root, db)
    root.geometry("+40+40")
    w._set_esercizio(vecchio)
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()

    controlli.append(("icona della finestra dal file .ico", tema.ICONA_DA_ICO))

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

    # 4. Saldi conti (albero dei conti e sottoconti) e partitario di un fornitore
    w.notebook.select(1)
    foto(root, "03-saldi-conti")
    conti = {c["codice"]: c["id"] for c in db.get_conti()}
    w._apri_partitario(str(conti["401"]))
    foto(root, "04-partitari")
    w.notebook.select(0)

    # 5. Dialoghi
    def dialogo(crea, nome):
        finestra = crea()
        finestra.attributes("-topmost", True)
        foto(finestra, nome)
        finestra.destroy()

    def scelta_conti():
        d = dialogs.SelezioneContiDialog(root, db.get_conti(), "Partitari", None, solo_economici=True)
        d._da_var.set("401")
        d._a_var.set("404")
        d._spunta_intervallo()
        return d

    dialogo(scelta_conti, "05-scelta-conti")
    dialogo(lambda: dialogs.RiportoSaldiDialog(root, db, nuovo, vecchio), "06-riporto-saldi")
    dialogo(lambda: dialogs.GestioneContiDialog(root, db), "07-piano-dei-conti")
    dialogo(lambda: dialogs.GestioneEserciziDialog(root, db, vecchio), "08-esercizi")

    # 6. Moduli IVA e bilancio, su un archivio nuovo con il piano dei conti completo
    import bilancio_ui
    import iva_ui
    from iva import ACQUISTI, FATTURA, VENDITE, ModuloIva
    completo = Database(os.path.join(cartella, "completo.db"))
    completo.connect()
    completo.init_db("completo")
    for chiave, valore in (("azienda_denominazione", "Laboratorio Esempio S.r.l."), ("azienda_partita_iva", "01234567890")):
        completo.set_impostazione(chiave, valore)
    es_prec = completo.crea_esercizio("Esercizio 2025", "2025-01-01", "2025-12-31")
    es_c = completo.crea_esercizio("Esercizio 2026", "2026-01-01", "2026-12-31")
    k = {c["codice"]: c["id"] for c in completo.get_conti()}
    m = ModuloIva(completo)
    al = {a["codice"]: a["id"] for a in m.get_aliquote()}
    rg = {r["tipo"]: r["id"] for r in m.get_registri()}
    for es, anno, fattore in ((es_prec, 2025, 0.8), (es_c, 2026, 1.0)):
        completo.crea_registrazione(es, f"{anno}-01-02", "Versamento soci", [(k["2501"], 10000, 0), (k["3101"], 0, 10000)]) if anno == 2025 else None
        for mese in range(1, 13):
            d = f"{anno}-{mese:02d}-15"
            m.registra_documento(es, rg[VENDITE], d, f"Fattura vendita {mese}", k["2201"],
                                 [{"conto_id": k["5101"], "imponibile": round(4000 * fattore, 2), "imposta": round(880 * fattore, 2), "aliquota_id": al["22"]}])
            m.registra_documento(es, rg[ACQUISTI], d, f"Fattura acquisto {mese}", k["4401"],
                                 [{"conto_id": k["6101"], "imponibile": round(1500 * fattore, 2), "imposta": round(330 * fattore, 2), "aliquota_id": al["22"], "detraibile": 100}])
            completo.crea_registrazione(es, f"{anno}-{mese:02d}-28", "Incasso clienti", [(k["2501"], round(4880 * fattore, 2), 0), (k["2201"], 0, round(4880 * fattore, 2))])
            completo.crea_registrazione(es, f"{anno}-{mese:02d}-28", "Pagamento fornitori", [(k["4401"], round(1830 * fattore, 2), 0), (k["2501"], 0, round(1830 * fattore, 2))])
            completo.crea_registrazione(es, f"{anno}-{mese:02d}-05", "Affitto laboratorio", [(k["6301"], 800, 0), (k["2501"], 0, 800)])
    principale_db = w.db
    dialogo(lambda: bilancio_ui.BilancioDialog(root, completo, es_c, esporta=lambda *a: None), "11-bilancio")
    es_c_riga = completo.get_esercizio(es_c)
    def fattura():
        d = iva_ui.DocumentoIvaDialog(root, completo, es_c_riga, ACQUISTI, FATTURA)
        d._data_reg.set_iso_date("2026-11-05")
        d._data_doc.set_iso_date("2026-11-03")
        d._numero.insert(0, "123/26")
        d._controparte.set_value(next(x for x in d._conti_labels if x.startswith("4401")))
        r = d._righe[0]
        r["conto"].set_value(next(x for x in d._conti_labels if x.startswith("6101")))
        r["importo"].set_amount(1000)
        d._ricalcola(r)
        d._aggiorna()
        return d
    dialogo(fattura, "12-fattura-acquisto")
    completo.set_impostazione("iva_periodicita", "T")
    def liquidazione():
        d = iva_ui.LiquidazioneDialog(root, completo, esporta=lambda *a: None, aggiorna_giornale=lambda: None)
        d._periodo.anno.set(2026)
        d._periodo.periodo.current(2)
        d._calcola()
        return d
    dialogo(liquidazione, "13-liquidazione-iva")
    def collega():
        d = bilancio_ui.CollegaContiDialog(root, principale_db)
        d._proposte = {c["id"]: p for c in principale_db.get_conti() if not c["voce_bilancio"]
                       for p in [bilancio_ui.proponi(c)] if p}
        d._popola()
        return d
    dialogo(collega, "14-collega-conti")

    # 7. Schermo intero: barra delle applicazioni con l'icona
    from PIL import ImageGrab
    ImageGrab.grab(all_screens=True).save(os.path.join(USCITA, "09-schermo-intero.png"))

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
