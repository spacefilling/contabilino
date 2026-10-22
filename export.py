"""
Contabilino - Export CSV, Excel e PDF
Libro giornale, saldi conti, costi e ricavi, partitari dei conti.

Ogni report viene prima costruito come tabella (colonne e sezioni di righe),
poi scritto nel formato scelto: CSV, Excel e PDF contengono gli stessi dati.
Gli export leggono soltanto il database, con le stesse query delle schede.
Le registrazioni con più righe (es. fatture con IVA) sono gestite ovunque.
"""

import csv
from dataclasses import dataclass, field
from datetime import date

from dateutils import format_display as _format_date, periodo_label

FORMATI = {
    "csv": ("CSV", ".csv"),
    "xlsx": ("Excel", ".xlsx"),
    "pdf": ("PDF", ".pdf"),
}

TIPI_ECONOMICI = ("COSTO", "RICAVO")

# Verso naturale del saldo: +1 = Dare - Avere, -1 = Avere - Dare
SEGNO_SALDO = {"ATTIVO": 1, "COSTO": 1, "PASSIVO": -1, "RICAVO": -1}
NATURA = {"ATTIVO": "conto di attivo", "PASSIVO": "conto di passivo",
          "COSTO": "conto di costo", "RICAVO": "conto di ricavo"}


# --- Struttura comune dei report ---

@dataclass
class Colonna:
    titolo: str
    tipo: str = "testo"  # "testo", "centro" (numeri e date) oppure "importo"
    larghezza: float = 12  # in caratteri; nel PDF conta la proporzione tra le colonne


@dataclass
class Riga:
    valori: list
    grassetto: bool = False
    rientro: int = 0  # livelli di rientro della colonna del nome conto (sottoconti)


@dataclass
class Sezione:
    righe: list
    titolo: str = ""
    intestazioni: bool = True  # mostra la riga con i titoli delle colonne


@dataclass
class Report:
    titolo: str
    sottotitolo: str  # esercizio e periodo
    colonne: list
    sezioni: list
    colonna_nome: int = 1  # colonna a cui si applica il rientro dei sottoconti
    note: str = ""
    orizzontale: bool = False  # PDF in A4 orizzontale
    # Per il CSV: una tabella unica (intestazioni, righe) al posto delle sezioni
    csv_piatto: tuple = None
    nome_foglio: str = "Report"
    vuoto: bool = field(default=False)  # nessun dato da esportare
    filtro: str = ""  # conti scelti, se l'export non comprende tutti i conti
    prefisso_pagina: str = ""  # es. "2026/": pagine numerate per anno (registri IVA)


def _sottotitolo(db, esercizio_id):
    e = db.get_esercizio(esercizio_id)
    return f"{e['descrizione']}  ({periodo_label(e['data_inizio'], e['data_fine'])})"


def _conto(codice, nome):
    return f"{codice} - {nome}"


def _descrivi_selezione(db, conto_ids):
    """Riga d'intestazione con i conti scelti ("" se l'export comprende tutti i conti)."""
    if conto_ids is None:
        return ""
    scelti = set(conto_ids)
    codici = [c["codice"] for c in db.get_conti() if c["id"] in scelti]
    if len(codici) == 1:
        return f"Selezione: conto {codici[0]}"
    if len(codici) <= 12:
        return f"Selezione: conti {', '.join(codici)}"
    return f"Selezione: {len(codici)} conti ({', '.join(codici[:10])}, ...)"


def _ha_movimenti(saldo):
    return round(saldo["totale_dare"], 2) != 0 or round(saldo["totale_avere"], 2) != 0


# --- Report ---

def report_giornale(db, esercizio_id):
    """
    Libro giornale. Se tutte le registrazioni hanno un conto in Dare e uno in Avere
    resta il formato compatto di sempre (una riga per registrazione); se ce n'è almeno
    una con più righe (es. fattura con IVA) si usa il formato classico, una riga per
    conto movimentato, con Dare e Avere separati.
    """
    rows = db.get_giornale_export(esercizio_id)
    sottotitolo = _sottotitolo(db, esercizio_id)
    if all(r["semplice"] for r in rows):
        righe = [
            Riga([
                row["numero"],
                _format_date(row["data"]),
                row["descrizione"],
                _conto(row["dare_codice"], row["dare_nome"]),
                _conto(row["avere_codice"], row["avere_nome"]),
                row["importo"],
            ])
            for row in rows
        ]
        return Report(
            titolo="Libro Giornale",
            sottotitolo=sottotitolo,
            colonne=[
                Colonna("N.", "centro", 6),
                Colonna("Data", "centro", 12),
                Colonna("Causale", "testo", 34),
                Colonna("Conto Dare", "testo", 26),
                Colonna("Conto Avere", "testo", 26),
                Colonna("Importo", "importo", 14),
            ],
            sezioni=[Sezione(righe)],
            colonna_nome=None,
            orizzontale=True,
            nome_foglio="Libro Giornale",
            vuoto=not righe,
        )

    righe = []
    tot_dare = tot_avere = 0
    for row in rows:
        for k, riga in enumerate(row["righe"]):
            prima = k == 0
            righe.append(Riga([
                row["numero"] if prima else "",
                _format_date(row["data"]) if prima else "",
                row["descrizione"] if prima else "",
                _conto(riga["codice"], riga["nome"]),
                riga["dare"] or None,
                riga["avere"] or None,
            ], rientro=0 if riga["dare"] else 1))
            tot_dare += riga["dare"]
            tot_avere += riga["avere"]
    righe.append(Riga(["", "", "TOTALE", "", tot_dare, tot_avere], grassetto=True))
    return Report(
        titolo="Libro Giornale",
        sottotitolo=sottotitolo,
        colonne=[
            Colonna("N.", "centro", 6),
            Colonna("Data", "centro", 12),
            Colonna("Causale", "testo", 40),
            Colonna("Conto", "testo", 36),
            Colonna("Dare", "importo", 14),
            Colonna("Avere", "importo", 14),
        ],
        sezioni=[Sezione(righe)],
        colonna_nome=3,
        note="Una riga per ogni conto movimentato; i conti in Avere sono rientrati.",
        orizzontale=True,
        nome_foglio="Libro Giornale",
        vuoto=not rows,
    )


def report_saldi(db, esercizio_id, conto_ids=None):
    """
    Saldi di tutti i conti (o di quelli scelti), come nella scheda Saldi Conti:
    un conto con sottoconti riporta in grassetto il totale del gruppo, con sotto
    i sottoconti e l'eventuale riga dei movimenti registrati direttamente sul padre.
    Il totale in fondo somma ogni conto una volta sola.
    """
    rows = db.get_saldi(esercizio_id)
    if conto_ids is not None:
        scelti = set(conto_ids)
        rows = [r for r in rows if r["id"] in scelti]
    ids = {r["id"] for r in rows}
    figli = {}
    for r in rows:
        if r["padre_id"] in ids:
            figli.setdefault(r["padre_id"], []).append(r)

    def riga(r, nome=None, dare=None, avere=None, **opzioni):
        dare = r["totale_dare"] if dare is None else dare
        avere = r["totale_avere"] if avere is None else avere
        return Riga([r["codice"], nome or r["nome"], r["tipo"], dare, avere, dare - avere], **opzioni)

    righe = []
    for r in rows:
        if r["padre_id"] in ids:
            continue  # sottoconto: compare sotto il suo padre
        sotto = figli.get(r["id"], [])
        if not sotto:
            # Conto senza sottoconti (o sottoconto scelto senza il suo padre)
            righe.append(riga(r, rientro=1 if r["padre_id"] else 0))
            continue
        dare = r["totale_dare"] + sum(f["totale_dare"] for f in sotto)
        avere = r["totale_avere"] + sum(f["totale_avere"] for f in sotto)
        righe.append(riga(r, dare=dare, avere=avere, grassetto=True))
        if _ha_movimenti(r):
            righe.append(riga(r, nome="registrato direttamente sul conto", rientro=1))
        righe.extend(riga(f, rientro=1) for f in sotto)

    tot_dare = sum(r["totale_dare"] for r in rows)
    tot_avere = sum(r["totale_avere"] for r in rows)
    righe.append(Riga(["", "TOTALE", "", tot_dare, tot_avere, tot_dare - tot_avere], grassetto=True))
    return Report(
        titolo="Saldi Conti",
        sottotitolo=_sottotitolo(db, esercizio_id),
        colonne=[
            Colonna("Codice", "centro", 10),
            Colonna("Conto", "testo", 32),
            Colonna("Tipo", "centro", 11),
            Colonna("Totale Dare", "importo", 14),
            Colonna("Totale Avere", "importo", 14),
            Colonna("Saldo", "importo", 14),
        ],
        sezioni=[Sezione(righe)],
        note="Saldo = Totale Dare - Totale Avere. Un conto con sottoconti riporta in grassetto "
             "il totale del gruppo; il TOTALE in fondo conta ogni conto una volta sola.",
        nome_foglio="Saldi Conti",
        vuoto=not rows,
        filtro=_descrivi_selezione(db, conto_ids),
    )


def _righe_economiche(saldi, tipo, scelti=None):
    """
    Righe dei conti di un tipo (COSTO o RICAVO) che hanno movimenti, con il totale.
    Importi con il segno naturale: i costi in Dare, i ricavi in Avere sono positivi.
    Un conto con sottoconti mostra in grassetto il totale del gruppo e, sotto,
    i sottoconti; gli eventuali movimenti registrati sul conto stesso hanno una riga a sé.
    scelti: id dei conti da includere (None = tutti). Un conto padre non scelto
    compare lo stesso come intestazione dei suoi sottoconti scelti.
    """
    segno = 1 if tipo == "COSTO" else -1

    def importo(r):
        return segno * (r["totale_dare"] - r["totale_avere"])

    def diretti(r):
        return (scelti is None or r["id"] in scelti) and _ha_movimenti(r)

    conti = [r for r in saldi if r["tipo"] == tipo]
    ids = {r["id"] for r in conti}
    figli = {}
    for r in conti:
        if r["padre_id"] in ids and diretti(r):
            figli.setdefault(r["padre_id"], []).append(r)

    righe = []
    totale = 0
    for r in conti:
        if r["padre_id"] in ids:
            continue  # sottoconto: compare sotto il suo conto padre
        sotto = figli.get(r["id"], [])
        if sotto:
            proprio = importo(r) if diretti(r) else 0
            gruppo = proprio + sum(importo(f) for f in sotto)
            righe.append(Riga([r["codice"], r["nome"], gruppo], grassetto=True))
            if diretti(r):
                righe.append(Riga([r["codice"], "registrato direttamente sul conto", importo(r)], rientro=1))
            for f in sotto:
                righe.append(Riga([f["codice"], f["nome"], importo(f)], rientro=1))
            totale += gruppo
        elif diretti(r):
            # Qui arrivano i conti principali e i sottoconti di un padre di altro tipo:
            # senza rientro, perché il padre non è in questa sezione
            righe.append(Riga([r["codice"], r["nome"], importo(r)]))
            totale += importo(r)
    return righe, totale


def report_costi_ricavi(db, esercizio_id, conto_ids=None):
    saldi = db.get_saldi(esercizio_id)
    scelti = None if conto_ids is None else set(conto_ids)
    righe_costi, tot_costi = _righe_economiche(saldi, "COSTO", scelti)
    righe_ricavi, tot_ricavi = _righe_economiche(saldi, "RICAVO", scelti)
    nessun_costo = Riga(["", "Nessun costo registrato", None])
    nessun_ricavo = Riga(["", "Nessun ricavo registrato", None])

    risultato = tot_ricavi - tot_costi
    if round(risultato, 2) >= 0:
        voce_risultato = "UTILE (ricavi - costi)"
    else:
        voce_risultato = "PERDITA (costi - ricavi)"

    return Report(
        titolo="Costi e Ricavi",
        sottotitolo=_sottotitolo(db, esercizio_id),
        colonne=[
            Colonna("Codice", "centro", 10),
            Colonna("Conto", "testo", 44),
            Colonna("Importo", "importo", 16),
        ],
        sezioni=[
            Sezione(
                (righe_costi or [nessun_costo]) + [Riga(["", "TOTALE COSTI", tot_costi], grassetto=True)],
                titolo="Costi",
            ),
            Sezione(
                (righe_ricavi or [nessun_ricavo]) + [Riga(["", "TOTALE RICAVI", tot_ricavi], grassetto=True)],
                titolo="Ricavi",
            ),
            Sezione(
                [
                    Riga(["", "Totale ricavi", tot_ricavi]),
                    Riga(["", "Totale costi", tot_costi]),
                    Riga(["", voce_risultato, abs(risultato)], grassetto=True),
                ],
                titolo="Risultato" if conto_ids is None else "Risultato dei conti selezionati",
                intestazioni=False,
            ),
        ],
        note="Solo i conti di tipo COSTO e RICAVO con movimenti nell'esercizio. "
             "Un conto con sottoconti riporta in grassetto il totale del gruppo.",
        nome_foglio="Costi e Ricavi",
        vuoto=not righe_costi and not righe_ricavi,
        filtro=_descrivi_selezione(db, conto_ids),
    )


def conti_economici(db):
    """Conti di costo e ricavo in ordine gerarchico (per scegliere cosa esportare)."""
    return [c for c in db.get_conti() if c["tipo"] in TIPI_ECONOMICI]


def report_partitari(db, esercizio_id, conto_ids=None):
    """
    Partitari: per ogni conto i movimenti dell'esercizio con data, numero,
    causale e contropartita, e il saldo progressivo nel verso naturale del conto.
    conto_ids: conti da includere (None = tutti i conti).
    Compaiono solo i conti che nell'esercizio hanno movimenti.
    """
    conti = list(db.get_conti())
    if conto_ids is not None:
        scelti = set(conto_ids)
        conti = [c for c in conti if c["id"] in scelti]
    movimenti = movimenti_partitario(db, esercizio_id, [c["id"] for c in conti])

    sezioni = []
    piatte = []
    for c in conti:
        voci = movimenti[c["id"]]
        if not voci:
            continue
        segno = SEGNO_SALDO[c["tipo"]]
        righe = []
        saldo = tot_dare = tot_avere = 0
        for reg, contropartita, dare, avere in voci:
            tot_dare += dare
            tot_avere += avere
            saldo += segno * (dare - avere)
            valori = [
                _format_date(reg["data"]), reg["numero"], reg["descrizione"],
                contropartita, dare or None, avere or None, saldo,
            ]
            righe.append(Riga(valori))
            piatte.append([c["codice"], c["nome"]] + valori)
        righe.append(Riga(["", "", "TOTALE", "", tot_dare, tot_avere, saldo], grassetto=True))
        sezioni.append(Sezione(righe, titolo=f"{_conto(c['codice'], c['nome'])}  ({NATURA[c['tipo']]})"))

    colonne = [
        Colonna("Data", "centro", 11),
        Colonna("N.", "centro", 6),
        Colonna("Causale", "testo", 32),
        Colonna("Contropartita", "testo", 26),
        Colonna("Dare", "importo", 13),
        Colonna("Avere", "importo", 13),
        Colonna("Saldo", "importo", 13),
    ]
    return Report(
        titolo="Partitari",
        sottotitolo=_sottotitolo(db, esercizio_id),
        colonne=colonne,
        sezioni=sezioni,
        colonna_nome=None,
        note="Saldo progressivo: Dare - Avere per i conti di attivo e di costo, "
             "Avere - Dare per i conti di passivo e di ricavo.",
        csv_piatto=(["Codice conto", "Conto"] + [col.titolo for col in colonne], piatte),
        nome_foglio="Partitari",
        vuoto=not sezioni,
        filtro=_descrivi_selezione(db, conto_ids),
    )


def movimenti_partitario(db, esercizio_id, conto_ids):
    """
    Movimenti dei conti indicati nell'esercizio, in ordine di data e numero:
    {conto_id: [(registrazione, contropartita, dare, avere), ...]}.
    Ogni registrazione ha un conto in Dare e uno in Avere: finisce nel partitario
    di ciascuno dei due, con l'altro come contropartita.
    """
    movimenti = {cid: [] for cid in conto_ids}
    for reg in db.get_registrazioni_compatte(esercizio_id):
        for riga in reg["righe"]:
            if riga["conto_id"] not in movimenti:
                continue
            movimenti[riga["conto_id"]].append(
                (reg, contropartita(reg, riga), riga["dare"], riga["avere"])
            )
    return movimenti


def contropartita(reg, riga):
    """
    L'altro conto della registrazione rispetto a una sua riga: il conto del lato
    opposto se è uno solo, altrimenti "Diversi" con i codici (es. fattura con IVA).
    """
    opposti = [x for x in reg["righe"] if (x["avere"] if riga["dare"] else x["dare"])]
    if len(opposti) == 1:
        return _conto(opposti[0]["codice"], opposti[0]["nome"])
    return "Diversi: " + ", ".join(x["codice"] for x in opposti)


# --- Registri IVA e liquidazione (modulo IVA) ---

def intestazione_azienda(db):
    """ "Ragione sociale - P.IVA ..." per l'intestazione delle stampe fiscali ("" se non impostata)."""
    parti = [db.get_impostazione("azienda_denominazione") or ""]
    if db.get_impostazione("azienda_partita_iva"):
        parti.append(f"P.IVA {db.get_impostazione('azienda_partita_iva')}")
    if db.get_impostazione("azienda_codice_fiscale"):
        parti.append(f"C.F. {db.get_impostazione('azienda_codice_fiscale')}")
    return "  -  ".join(p for p in parti if p)


def report_registro_iva(db, registro_id, dal, al, nome_periodo):
    """
    Registro IVA (vendite, acquisti o corrispettivi) del periodo: una riga per
    aliquota di ogni documento, in ordine di protocollo, e il riepilogo per aliquota.
    Le note di credito hanno importi negativi.
    """
    from iva import ACQUISTI, ModuloIva
    modulo = ModuloIva(db)
    registro = modulo.get_registro(registro_id)
    acquisti = registro["tipo"] == ACQUISTI
    righe = []
    documento = None
    for r in modulo.righe_registro(registro_id, dal, al):
        s = modulo.segno_documento(r["tipo_documento"])
        nuovo = r["documento_id"] != documento
        documento = r["documento_id"]
        tipo = {"NOTA_CREDITO": "NC", "AUTOFATTURA": "RC"}.get(r["tipo_documento"], "")
        if r["reverse_charge"] and not tipo:
            tipo = "RC"
        controparte = _conto(r["controparte_codice"], r["controparte_nome"]) if r["controparte_codice"] else ""
        valori = [
            r["protocollo"] if nuovo else "",
            _format_date(r["data_registrazione"]) if nuovo else "",
            _format_date(r["data_documento"]) if nuovo and r["data_documento"] else "",
            f"{r['numero_documento'] or ''} {tipo}".strip() if nuovo else "",
            controparte if nuovo else "",
            r["aliquota_codice"],
            s * r["imponibile"],
            s * r["imposta"],
        ]
        if acquisti:
            valori.append(s * round(r["imposta"] * r["detraibile"] / 100, 2))
        righe.append(Riga(valori))

    riepilogo = []
    totali = modulo.totali_registro(registro_id, dal, al)
    for codice, tot in totali.items():
        valori = ["", "", "", "", tot["descrizione"], codice, tot["imponibile"], tot["imposta"]]
        if acquisti:
            valori.append(tot["detraibile"])
        riepilogo.append(Riga(valori))
    valori = ["", "", "", "", "TOTALE", "", sum(x["imponibile"] for x in totali.values()),
              sum(x["imposta"] for x in totali.values())]
    if acquisti:
        valori.append(sum(x["detraibile"] for x in totali.values()))
    riepilogo.append(Riga(valori, grassetto=True))

    colonne = [
        Colonna("Prot.", "centro", 6),
        Colonna("Data reg.", "centro", 10),
        Colonna("Data doc.", "centro", 10),
        Colonna("N. doc.", "testo", 10),
        Colonna("Conto di incasso" if registro["tipo"] == "CORRISPETTIVI" else
                "Fornitore" if acquisti else "Cliente", "testo", 30),
        Colonna("Aliquota", "centro", 8),
        Colonna("Imponibile", "importo", 13),
        Colonna("Imposta", "importo", 12),
    ]
    if acquisti:
        colonne.append(Colonna("Detraibile", "importo", 12))
    azienda = intestazione_azienda(db)
    return Report(
        titolo=f"{registro['descrizione']} ({registro['codice']})",
        sottotitolo=f"{nome_periodo}  ({_format_date(dal)} - {_format_date(al)})" + (f"  -  {azienda}" if azienda else ""),
        colonne=colonne,
        sezioni=[Sezione(righe or [Riga(["", "", "", "", "Nessun documento nel periodo", "", None, None] + ([None] if acquisti else []))]),
                 Sezione(riepilogo, titolo="Riepilogo per aliquota")],
        colonna_nome=None,
        note="NC = nota di credito (importi negativi); RC = fattura in reverse charge (nel registro "
             "vendite: integrazione dell'IVA della fattura d'acquisto).",
        orizzontale=True,
        nome_foglio=f"Registro {registro['codice']}"[:31],
        vuoto=False,
        prefisso_pagina=f"{dal[:4]}/",
    )


def report_liquidazione_iva(db, liq):
    """Prospetto della liquidazione IVA del periodo (dict di ModuloIva.calcola_liquidazione)."""
    debito, credito = [], []
    for d in liq["dettaglio"]:
        reg = d["registro"]
        nome = f"{reg['codice']} - {reg['descrizione']}"
        if d["debito"]:
            debito.append(Riga([nome, d["debito"]]))
        if d["credito"]:
            credito.append(Riga([nome, d["credito"]]))
    debito.append(Riga(["Totale IVA a debito", liq["iva_debito"]], grassetto=True))
    credito.append(Riga(["Totale IVA detraibile", liq["iva_credito"]], grassetto=True))
    calcolo = [
        Riga(["IVA a debito", liq["iva_debito"]]),
        Riga(["IVA detraibile", -liq["iva_credito"]]),
    ]
    if liq["credito_precedente"]:
        calcolo.append(Riga(["Credito del periodo precedente", -liq["credito_precedente"]]))
    if liq["debito_precedente"]:
        calcolo.append(Riga(["Debito del periodo precedente (sotto 25,82 €)", liq["debito_precedente"]]))
    if liq["interessi"]:
        calcolo.append(Riga(["Interessi 1% (liquidazione trimestrale)", liq["interessi"]]))
    if liq["acconto"]:
        calcolo.append(Riga(["Acconto versato", -liq["acconto"]]))
    risultato = liq["risultato"]
    if risultato < 0:
        esito = "CREDITO da riportare al periodo successivo"
    elif liq["da_versare"]:
        esito = "IVA DA VERSARE"
    else:
        esito = "Debito sotto 25,82 €: si riporta al periodo successivo"
    calcolo.append(Riga([esito, abs(risultato)], grassetto=True))
    azienda = intestazione_azienda(db)
    return Report(
        titolo=f"Liquidazione IVA - {liq['nome']}",
        sottotitolo=f"Periodo {_format_date(liq['dal'])} - {_format_date(liq['al'])}  -  "
                    f"liquidazione {'mensile' if liq['periodicita'] == 'M' else 'trimestrale'}"
                    + (f"  -  {azienda}" if azienda else ""),
        colonne=[Colonna("Voce", "testo", 60), Colonna("Importo", "importo", 18)],
        sezioni=[Sezione(debito, titolo="IVA a debito (vendite e corrispettivi)"),
                 Sezione(credito, titolo="IVA detraibile (acquisti)"),
                 Sezione(calcolo, titolo="Liquidazione", intestazioni=False)],
        colonna_nome=None,
        note="Il versamento (F24) e l'eventuale acconto di dicembre si registrano a parte.",
        nome_foglio="Liquidazione IVA",
        prefisso_pagina=f"{liq['anno']}/",
    )


# --- Bilancio civilistico (modulo bilancio) ---

def report_bilancio(db, bilancio, schema, esercizio, esercizio_precedente=None, voci_nulle=False):
    """
    Stato patrimoniale e conto economico nello schema scelto ("ordinario",
    "abbreviato" o "micro") dal risultato di bilancio.calcola_bilancio, con la
    colonna dell'esercizio precedente se calcolata.
    """
    from bilancio import senza_voci_nulle
    from bilancio_schemi import NOMI_SCHEMI
    prospetto = getattr(bilancio, schema)
    con_precedente = prospetto.valori_precedenti is not None

    def righe(elenco):
        if not voci_nulle:
            elenco = senza_voci_nulle(elenco)
        risultato = []
        for r in elenco:
            forte = r.genere in ("INTESTAZIONE", "TOTALE", "RISULTATO")
            valori = [r.etichetta, r.importo]
            if con_precedente:
                valori.append(r.importo_precedente)
            risultato.append(Riga(valori, grassetto=forte, rientro=r.livello))
        return risultato

    nome_corrente = esercizio["descrizione"]
    colonne = [Colonna("Voce", "testo", 70), Colonna(nome_corrente, "importo", 16)]
    if con_precedente:
        colonne.append(Colonna(esercizio_precedente["descrizione"] if esercizio_precedente else "Precedente",
                               "importo", 16))
    azienda = intestazione_azienda(db)
    return Report(
        titolo=NOMI_SCHEMI.get(schema, schema),
        sottotitolo=f"{esercizio['descrizione']}  ({periodo_label(esercizio['data_inizio'], esercizio['data_fine'])})"
                    + (f"  -  {azienda}" if azienda else ""),
        colonne=colonne,
        sezioni=[Sezione(righe(prospetto.stato_patrimoniale), titolo="Stato patrimoniale"),
                 Sezione(righe(prospetto.conto_economico), titolo="Conto economico")],
        colonna_nome=0,
        note="Importi in euro." + ("" if voci_nulle else " Le voci con importo nullo in entrambi gli esercizi "
                                                       "non sono riportate."),
        nome_foglio="Bilancio",
    )


REPORT = {
    "giornale": report_giornale,
    "saldi": report_saldi,
    "costi_ricavi": report_costi_ricavi,
    "partitari": report_partitari,
}


def crea_report(db, esercizio_id, tipo, **opzioni):
    return REPORT[tipo](db, esercizio_id, **opzioni)


def salva_report(report, filepath, formato="csv"):
    if formato == "xlsx":
        _salva_xlsx(report, filepath)
    elif formato == "pdf":
        _salva_pdf(report, filepath)
    else:
        _salva_csv(report, filepath)


# Compatibilità con le chiamate precedenti

def export_giornale(db, esercizio_id, filepath, formato="csv"):
    salva_report(report_giornale(db, esercizio_id), filepath, formato)


def export_saldi(db, esercizio_id, filepath, formato="csv"):
    salva_report(report_saldi(db, esercizio_id), filepath, formato)


# --- Formattazione ---

def _arrotonda(valore):
    """Due decimali, senza lo zero negativo dei calcoli in virgola mobile (-0,00)."""
    return round(valore, 2) + 0.0


def _importo_csv(valore):
    return "" if valore is None else f"{_arrotonda(valore):.2f}".replace(".", ",")


def _importo_it(valore):
    """1234.5 → 1.234,50 (None → vuoto)."""
    if valore is None:
        return ""
    s = f"{_arrotonda(valore):,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _valori_testo(report, riga, rientro="  "):
    """Valori della riga con il rientro dei sottoconti applicato alla colonna del nome."""
    valori = list(riga.valori)
    if riga.rientro and report.colonna_nome is not None:
        valori[report.colonna_nome] = rientro * riga.rientro + str(valori[report.colonna_nome])
    return valori


# --- CSV ---

def _salva_csv(report, filepath):
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        if report.csv_piatto:
            intestazioni, righe = report.csv_piatto
            tipi = ["testo", "testo"] + [c.tipo for c in report.colonne]
            writer.writerow(intestazioni)
            for valori in righe:
                writer.writerow([
                    _importo_csv(v) if t == "importo" else ("" if v is None else v)
                    for v, t in zip(valori, tipi)
                ])
            return

        writer.writerow([c.titolo for c in report.colonne])
        for i, sezione in enumerate(report.sezioni):
            if sezione.titolo:
                if i:
                    writer.writerow([])
                writer.writerow([sezione.titolo.upper()])
            for riga in sezione.righe:
                writer.writerow([
                    _importo_csv(v) if c.tipo == "importo" else ("" if v is None else v)
                    for v, c in zip(_valori_testo(report, riga), report.colonne)
                ])


# --- Excel ---

def _salva_xlsx(report, filepath):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    formato_importo = "#,##0.00"  # Excel lo mostra con le impostazioni locali (1.234,56)
    grassetto = Font(bold=True)
    grigio = PatternFill("solid", fgColor="E8E8E8")
    linea = Side(style="thin", color="808080")

    wb = Workbook()
    ws = wb.active
    ws.title = report.nome_foglio[:31]

    ws.cell(row=1, column=1, value=report.titolo).font = Font(bold=True, size=14)
    ws.cell(row=2, column=1, value=report.sottotitolo)
    r = 4
    if report.filtro:
        ws.cell(row=3, column=1, value=report.filtro).font = Font(italic=True)
        r = 5
    riga_intestazioni = r

    for i, sezione in enumerate(report.sezioni):
        if sezione.titolo:
            if i:
                r += 1
            ws.cell(row=r, column=1, value=sezione.titolo).font = Font(bold=True, size=12)
            r += 1
        if sezione.intestazioni:
            for col, c in enumerate(report.colonne, 1):
                cell = ws.cell(row=r, column=col, value=c.titolo)
                cell.font = grassetto
                cell.fill = grigio
                cell.border = Border(bottom=linea)
                if c.tipo == "importo":
                    cell.alignment = Alignment(horizontal="right")
                elif c.tipo == "centro":
                    cell.alignment = Alignment(horizontal="center")
            if len(report.sezioni) == 1:
                ws.freeze_panes = ws.cell(row=r + 1, column=1)
            r += 1
        for riga in sezione.righe:
            for col, (v, c) in enumerate(zip(riga.valori, report.colonne), 1):
                if v is None or v == "":
                    cell = ws.cell(row=r, column=col)
                else:
                    cell = ws.cell(row=r, column=col, value=_arrotonda(v) if c.tipo == "importo" else v)
                if c.tipo == "importo":
                    cell.number_format = formato_importo
                elif c.tipo == "centro":
                    cell.alignment = Alignment(horizontal="center")
                if col - 1 == report.colonna_nome and riga.rientro:
                    cell.alignment = Alignment(indent=2 * riga.rientro)
                if riga.grassetto:
                    cell.font = grassetto
                    cell.border = Border(top=linea)
            r += 1

    if report.note:
        ws.cell(row=r + 1, column=1, value=report.note).font = Font(italic=True, color="555555")

    for col, c in enumerate(report.colonne, 1):
        ws.column_dimensions[get_column_letter(col)].width = c.larghezza

    # Stampa: una pagina di larghezza, intestazioni ripetute se la tabella è unica
    ws.page_setup.orientation = "landscape" if report.orizzontale else "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    if len(report.sezioni) == 1 and report.sezioni[0].intestazioni:
        ws.print_title_rows = f"{riga_intestazioni}:{riga_intestazioni}"

    wb.save(filepath)


# --- PDF ---

def _salva_pdf(report, filepath):
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    pagina = landscape(A4) if report.orizzontale else A4
    margine = 15 * mm
    larghezza_utile = pagina[0] - 2 * margine
    stampato = date.today().strftime("%d/%m/%Y")

    base = ParagraphStyle("base", fontName="Helvetica", fontSize=8.5, leading=10.5)
    stili = {
        "testo": base,
        "centro": ParagraphStyle("centro", parent=base, alignment=TA_CENTER),
        "importo": ParagraphStyle("importo", parent=base, alignment=TA_RIGHT),
    }
    stili_bold = {k: ParagraphStyle(k + "_b", parent=s, fontName="Helvetica-Bold") for k, s in stili.items()}
    titolo_stile = ParagraphStyle("titolo", fontName="Helvetica-Bold", fontSize=15, leading=19)
    sotto_stile = ParagraphStyle("sotto", fontName="Helvetica", fontSize=10, leading=13,
                                 textColor=colors.HexColor("#444444"), spaceAfter=8)
    sezione_stile = ParagraphStyle("sezione", fontName="Helvetica-Bold", fontSize=11, leading=14,
                                   spaceBefore=10, spaceAfter=4, keepWithNext=True)
    filtro_stile = ParagraphStyle("filtro", fontName="Helvetica-Oblique", fontSize=9, leading=12,
                                  textColor=colors.HexColor("#444444"), spaceAfter=8)
    nota_stile = ParagraphStyle("nota", fontName="Helvetica-Oblique", fontSize=8, leading=10,
                                textColor=colors.HexColor("#555555"), spaceBefore=10)

    totale_larghezze = sum(c.larghezza for c in report.colonne)
    larghezze = [larghezza_utile * c.larghezza / totale_larghezze for c in report.colonne]

    def cella(valore, colonna, bold, rientro=0):
        if colonna.tipo == "importo":
            testo = _importo_it(valore)
        else:
            testo = escape("" if valore is None else str(valore))
        if rientro:
            testo = "&nbsp;" * 4 * rientro + testo
        return Paragraph(testo, (stili_bold if bold else stili)[colonna.tipo])

    def tabella(sezione):
        dati = []
        stile = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]
        if sezione.intestazioni:
            dati.append([
                Paragraph(escape(c.titolo), stili_bold[c.tipo]) for c in report.colonne
            ])
            stile += [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#808080")),
            ]
        for riga in sezione.righe:
            n = len(dati)
            dati.append([
                cella(v, c, riga.grassetto, riga.rientro if i == report.colonna_nome else 0)
                for i, (v, c) in enumerate(zip(riga.valori, report.colonne))
            ])
            if riga.grassetto:
                stile.append(("LINEABOVE", (0, n), (-1, n), 0.6, colors.HexColor("#808080")))
            elif n % 2 == 0:
                stile.append(("BACKGROUND", (0, n), (-1, n), colors.HexColor("#F6F6F6")))
        t = Table(dati, colWidths=larghezze, repeatRows=1 if sezione.intestazioni else 0)
        t.setStyle(TableStyle(stile))
        return t

    contenuto = [Paragraph(escape(report.titolo), titolo_stile)]
    if report.filtro:
        contenuto += [
            Paragraph(escape(report.sottotitolo), ParagraphStyle("sotto_f", parent=sotto_stile, spaceAfter=2)),
            Paragraph(escape(report.filtro), filtro_stile),
        ]
    else:
        contenuto.append(Paragraph(escape(report.sottotitolo), sotto_stile))
    if report.vuoto:
        contenuto.append(Paragraph("Nessun dato da esportare.", base))
    for sezione in report.sezioni:
        if sezione.titolo:
            contenuto.append(Paragraph(escape(sezione.titolo), sezione_stile))
        contenuto.append(tabella(sezione))
        contenuto.append(Spacer(1, 4))
    if report.note:
        contenuto.append(Paragraph(escape(report.note), nota_stile))

    piede_sinistra = f"Contabilino - {report.titolo} - {report.sottotitolo}"

    class CanvasNumerato(canvas.Canvas):
        """Scrive il piè di pagina alla fine, quando si conosce il numero totale di pagine."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pagine = []

        def showPage(self):
            self._pagine.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            totale = len(self._pagine)
            for stato in self._pagine:
                self.__dict__.update(stato)
                self.setFont("Helvetica", 7.5)
                self.setFillColor(colors.HexColor("#666666"))
                destra = f"Stampato il {stampato}  -  Pagina {report.prefisso_pagina}{self._pageNumber} di {totale}"
                # Il testo a sinistra si accorcia se non ci sta accanto al numero di pagina
                spazio = pagina[0] - 2 * margine - stringWidth(destra, "Helvetica", 7.5) - 8 * mm
                sinistra = piede_sinistra
                while sinistra and stringWidth(sinistra, "Helvetica", 7.5) > spazio:
                    sinistra = sinistra[:-2].rstrip() + "…" if len(sinistra) > 2 else ""
                    sinistra = sinistra.replace("……", "…")
                self.drawString(margine, 9 * mm, sinistra)
                self.drawRightString(pagina[0] - margine, 9 * mm, destra)
                super().showPage()
            super().save()

    doc = SimpleDocTemplate(
        filepath, pagesize=pagina,
        leftMargin=margine, rightMargin=margine, topMargin=margine, bottomMargin=18 * mm,
        title=f"{report.titolo} - {report.sottotitolo}", author="Contabilino",
    )
    doc.build(contenuto, canvasmaker=CanvasNumerato)
