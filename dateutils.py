"""
Contabilino - Utility per le date
Conversione tra formato ISO (usato dal database) e formato italiano
GG/MM/AAAA (usato dall'interfaccia), calcolo del periodo dell'esercizio.
"""

from datetime import date, timedelta


def parse_iso(iso_date):
    """Converte 'AAAA-MM-GG' in un oggetto date. None se non valida."""
    if not iso_date:
        return None
    parts = str(iso_date).split("-")
    if len(parts) != 3:
        return None
    try:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def to_iso(text):
    """
    Accetta GG/MM/AAAA, G/M/AAAA, GGMMAAAA, AAAAMMGG o AAAA-MM-GG
    e restituisce la data in formato ISO. Stringa vuota se non valida.
    """
    if not text:
        return ""
    raw = str(text).strip()
    if not raw:
        return ""

    # Forma con separatori: 12/02/2026, 12-02-2026, 12.02.2026, 2026-02-12
    for sep in ("/", "-", "."):
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep)]
            if len(parts) != 3:
                return ""
            if len(parts[0]) == 4:
                y, m, d = parts          # AAAA-MM-GG
            else:
                d, m, y = parts          # GG/MM/AAAA
            if len(y) == 2:
                y = "20" + y             # 1/2/26 → 2026
            return _data_iso(y, m, d)

    # Forma compatta di 8 cifre: 20260212 (AAAAMMGG) oppure 12022026 (GGMMAAAA).
    # Si prova la prima lettura e, se non è una data valida, la seconda:
    # così anche 25122026 è il 25/12/2026 e non un anno 2512.
    if len(raw) == 8 and raw.isdigit():
        return (_data_iso(raw[0:4], raw[4:6], raw[6:8])
                or _data_iso(raw[4:8], raw[2:4], raw[0:2]))

    return ""


def _data_iso(y, m, d):
    """Data ISO da anno, mese e giorno in testo; vuota se non valida o con anno prima del 1900."""
    try:
        if int(y) < 1900:
            return ""
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return ""


def format_display(iso_date):
    """Converte AAAA-MM-GG in GG/MM/AAAA per la visualizzazione."""
    if not iso_date:
        return ""
    if "/" in str(iso_date):
        return iso_date
    parts = str(iso_date).split("-")
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return iso_date


def fine_default(data_inizio_iso):
    """
    Data di fine proposta per un esercizio che inizia in data_inizio:
    dodici mesi meno un giorno (1/7/2026 -> 30/6/2027, 1/1/2026 -> 31/12/2026).
    """
    d = parse_iso(data_inizio_iso)
    if not d:
        return ""
    if d.month == 2 and d.day == 29:
        # Anno bisestile: l'esercizio finisce il 28 febbraio successivo
        return date(d.year + 1, 2, 28).isoformat()
    return (d.replace(year=d.year + 1) - timedelta(days=1)).isoformat()


def periodo_label(data_inizio_iso, data_fine_iso):
    """Periodo leggibile: '01/07/2026 - 30/06/2027'."""
    return f"{format_display(data_inizio_iso)} - {format_display(data_fine_iso)}"


def etichetta_anni(data_inizio_iso, data_fine_iso):
    """
    Etichetta breve dell'esercizio, usata per i nomi dei file esportati:
    '2026' se l'esercizio sta in un solo anno, '2026-2027' se è a cavallo.
    """
    inizio = parse_iso(data_inizio_iso)
    fine = parse_iso(data_fine_iso)
    if not inizio:
        return ""
    if not fine or fine.year == inizio.year:
        return str(inizio.year)
    return f"{inizio.year}-{fine.year}"


def descrizione_default(data_inizio_iso, data_fine_iso):
    """Descrizione proposta: 'Esercizio 2026' oppure 'Esercizio 2026/2027'."""
    etichetta = etichetta_anni(data_inizio_iso, data_fine_iso)
    if not etichetta:
        return "Esercizio"
    return f"Esercizio {etichetta.replace('-', '/')}"


def data_in_periodo(data_iso, data_inizio_iso, data_fine_iso):
    """True se la data cade dentro il periodo dell'esercizio (estremi inclusi)."""
    d = parse_iso(data_iso)
    inizio = parse_iso(data_inizio_iso)
    fine = parse_iso(data_fine_iso)
    if not d or not inizio or not fine:
        return False
    return inizio <= d <= fine
