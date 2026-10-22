"""
Contabilino - Bilancio civilistico
Stato patrimoniale e conto economico negli schemi ordinario (artt. 2424 e 2425
c.c.), abbreviato (art. 2435-bis) e delle micro-imprese (art. 2435-ter), calcolati
dai saldi dei conti, con la colonna dell'esercizio precedente (art. 2423-ter,
comma 5) e i controlli di quadratura.

Funzioni pure: ricevono i saldi (le righe di Database.get_saldi o dizionari con
codice, nome, tipo, totale_dare, totale_avere e, facoltativo, padre_codice) e il
collegamento dei conti alle voci, e restituiscono prospetti e avvisi. Non leggono
né scrivono il database e non conoscono l'interfaccia.

Uso tipico:
    import piano_base
    b = calcola_bilancio(db.get_saldi(esercizio_id), piano_base.MAPPA,
                         db.get_saldi(precedente_id),
                         rettifiche=piano_base.RETTIFICHE,
                         voci_saldo_opposto=piano_base.VOCI_SALDO_OPPOSTO)
    for riga in b.ordinario.stato_patrimoniale: ...
    for avviso in b.avvisi: ...

Come si calcola
---------------
1. Ogni conto con saldo diverso da zero va nella foglia dello schema ordinario a
   cui è collegato (mappa: codice del conto -> codice della voce). Un sottoconto
   non collegato prende la voce del suo conto padre. L'importo segue il verso
   della voce: Dare - Avere per attivo, costi e oneri; Avere - Dare per passivo,
   ricavi e proventi (vedi bilancio_schemi).
2. Il saldo di un conto opposto al segno normale della voce non viene compensato
   in silenzio: se il conto ha una voce per il saldo opposto (per esempio la banca
   con lo scoperto va tra i debiti verso banche) viene spostato lì, con un avviso
   informativo; altrimenti resta nella voce e riceve un avviso di attenzione. I
   conti di rettifica (fondi di ammortamento, resi...) hanno per natura il saldo
   opposto alla loro voce e sono segnalati solo nel caso contrario.
3. Il risultato del conto economico (voce 21) si somma al Passivo A.IX.
4. Gli importi delle foglie ordinarie alimentano i tre schemi: le voci
   dell'abbreviato e delle micro-imprese raggruppano foglie dell'ordinario, per cui
   i totali coincidono per costruzione (ed è comunque verificato).
5. Controlli: attivo = passivo, conti con saldo non classificati, conti collegati a
   voci inesistenti, tipo del conto incoerente con il prospetto, voci con importo
   di segno anomalo, saldo dei conti collegati direttamente ad A.IX, voci dei
   derivati nelle micro-imprese.

Limiti
------
- Il bilancio si calcola sui saldi così come sono: le scritture di assestamento
  (ammortamenti, ratei e risconti, rimanenze finali, TFR, imposte) devono essere
  già registrate, e le scritture di chiusura (epilogo dei costi e dei ricavi al
  conto Utile d'esercizio) non devono esserlo: dopo l'epilogo il conto economico
  risulta vuoto. Il caso è segnalato dall'avviso sui conti collegati ad A.IX.
- La scadenza entro/oltre l'esercizio successivo è quella della voce collegata
  al conto: il programma non ripartisce il saldo di un conto per scadenza.
- Nessuna compensazione automatica, neppure dove la prassi la ammette (debito per
  imposte correnti al netto degli acconti, OIC 25): va registrata con un
  giroconto. Il segno dei saldi è valutato conto per conto, non per partita: un
  conto clienti con saldo Dare complessivo che nasconde singoli clienti a credito
  non viene segnalato.
- Il confronto con l'esercizio precedente usa lo stesso collegamento dei conti,
  salvo indicare mappa_precedente: l'adattamento delle voci non comparabili e la
  relativa informativa in nota integrativa (art. 2423-ter, comma 5) restano a chi
  redige il bilancio.
- Con unita_di_euro=True ogni foglia è arrotondata all'unità di euro (art. 2423,
  comma 6), i totali e il risultato sono ricalcolati dalle foglie arrotondate e la
  differenza che ne nasce nello stato patrimoniale va nella riserva da
  arrotondamento (Passivo A.VI), come d'uso nella prassi. Il conto economico non
  ha bisogno di una voce di quadratura perché il risultato è ricalcolato.
- Il programma non sceglie la forma del bilancio (limiti dimensionali in
  bilancio_schemi), non redige nota integrativa, rendiconto finanziario (art.
  2425-ter) né le informazioni in calce richieste alle micro-imprese.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache

import bilancio_schemi as bs

# Gravità degli avvisi
ERRORE = "errore"              # il bilancio non è corretto (per esempio non quadra)
ATTENZIONE = "attenzione"      # da verificare
INFORMAZIONE = "informazione"  # scelta fatta dal programma, per trasparenza

CORRENTE = "corrente"
PRECEDENTE = "precedente"

# Genere delle righe dei prospetti
INTESTAZIONE = "intestazione"  # titolo di una voce che ha una riga di totale
VOCE = "voce"                  # voce con il suo importo
TOTALE = "totale"              # riga di totale di una voce
RISULTATO = "risultato"        # risultato intermedio o finale (voci calcolate)

TOLLERANZA = 0.005


@dataclass
class Avviso:
    gravita: str
    messaggio: str
    conto: str = None      # codice del conto interessato
    voce: str = None       # codice della voce interessata
    esercizio: str = CORRENTE


@dataclass
class Classificazione:
    """Importi delle foglie dello schema ordinario per un esercizio."""
    importi: dict          # foglia -> importo (A.IX comprende il risultato)
    conti: dict            # foglia -> [(codice del conto, importo)]
    risultato: float       # utile (perdita) dell'esercizio, voce 21
    avvisi: list = field(default_factory=list)
    non_classificati: list = field(default_factory=list)  # conti con saldo senza voce valida
    saldo_conti_utile: float = 0.0  # importo dei conti collegati direttamente ad A.IX


@dataclass
class RigaBilancio:
    codice: str
    etichetta: str
    livello: int           # rientro: 0 per attivo/passivo e per le sezioni del conto economico
    genere: str            # INTESTAZIONE, VOCE, TOTALE o RISULTATO
    importo: float = None
    importo_precedente: float = None
    conti: tuple = ()      # ((codice del conto, importo), ...) confluiti nella voce, solo per le foglie

    @property
    def grassetto(self):
        return self.genere in (INTESTAZIONE, TOTALE, RISULTATO)


@dataclass
class Prospetto:
    schema: str            # "ordinario", "abbreviato" o "micro"
    titolo: str
    stato_patrimoniale: list
    conto_economico: list
    valori: dict           # codice della voce -> importo dell'esercizio
    valori_precedenti: dict = None

    @property
    def totale_attivo(self):
        return self.valori[bs.ATTIVO]

    @property
    def totale_passivo(self):
        return self.valori[bs.PASSIVO]

    @property
    def risultato(self):
        return self.valori[bs.UTILE_ESERCIZIO_CE]

    def precedente(self, codice):
        return None if self.valori_precedenti is None else self.valori_precedenti.get(codice)


@dataclass
class Bilancio:
    ordinario: Prospetto
    abbreviato: Prospetto
    micro: Prospetto
    avvisi: list
    classificazione: Classificazione
    classificazione_precedente: Classificazione = None
    quadra: bool = True
    quadra_precedente: bool = None

    def prospetto(self, schema):
        return {"ordinario": self.ordinario, "abbreviato": self.abbreviato, "micro": self.micro}[schema]

    @property
    def errori(self):
        return [a for a in self.avvisi if a.gravita == ERRORE]


# --- Supporto ---

def _campo(riga, nome, predefinito=None):
    """Valore di una colonna da un dict o da una sqlite3.Row (predefinito se manca o è NULL)."""
    try:
        valore = riga[nome]
    except (KeyError, IndexError):
        return predefinito
    return predefinito if valore is None else valore


def _euro(valore):
    """Importo in formato italiano, per i messaggi: 1.234,56."""
    testo = f"{abs(valore):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if valore < 0 else "") + testo


def _arrotonda_euro(valore):
    return float(Decimal(str(round(valore, 2))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _importo(saldo, voce):
    """Importo della voce dato il saldo Dare - Avere di un conto."""
    return saldo if voce.saldo == bs.DARE_AVERE else -saldo


def _inverti(segno_atteso):
    return {"+": "-", "-": "+"}.get(segno_atteso, segno_atteso)


def _segno_anomalo(importo, segno_atteso):
    if segno_atteso == "+":
        return importo <= -TOLLERANZA
    if segno_atteso == "-":
        return importo >= TOLLERANZA
    return False


def _descrivi(voce_codice):
    return f"«{bs.percorso(voce_codice)}»"


@lru_cache(maxsize=None)
def _foglie(voce):
    return tuple(bs.foglie_di(voce))


def _voce_del_conto(codice, padre, mappa):
    """(voce, ereditata): la voce del conto o, se manca, quella del conto padre."""
    if codice in mappa and mappa[codice]:
        return mappa[codice], False
    if padre and mappa.get(padre):
        return mappa[padre], True
    return None, False


# --- Calcolo ---

def classifica_conti(saldi, mappa, rettifiche=(), voci_saldo_opposto=None, esercizio=CORRENTE):
    """
    Porta i saldi dei conti nelle foglie dello schema ordinario (passi 1 e 2 del
    calcolo). Il risultato dell'esercizio non è ancora sommato ad A.IX: lo fa
    importi_esercizio. Restituisce una Classificazione con risultato a zero.
    """
    rettifiche = set(rettifiche or ())
    opposte = voci_saldo_opposto or {}
    importi = {f: 0.0 for f in bs.FOGLIE_ORDINARIO}
    conti = {}
    avvisi = []
    non_classificati = []
    saldo_utile = 0.0

    def avviso(gravita, messaggio, conto=None, voce=None):
        avvisi.append(Avviso(gravita, messaggio, conto, voce, esercizio))

    for r in saldi:
        codice = str(_campo(r, "codice", ""))
        nome = _campo(r, "nome", "")
        tipo = _campo(r, "tipo", "")
        padre = _campo(r, "padre_codice")
        saldo = round(float(_campo(r, "totale_dare", 0)) - float(_campo(r, "totale_avere", 0)), 2)
        conto = f"{codice} - {nome}"
        codice_voce, ereditata = _voce_del_conto(codice, padre, mappa)

        if codice_voce is not None and not bs.voce_collegabile(codice_voce):
            if abs(saldo) >= TOLLERANZA:
                non_classificati.append(codice)
                avviso(ERRORE, f"Il conto {conto} (saldo {_euro(saldo)}) è collegato a \"{codice_voce}\", "
                               "che non è una voce di dettaglio dello schema ordinario: l'importo resta "
                               "fuori dal bilancio.", codice, codice_voce)
            else:
                avviso(ATTENZIONE, f"Il conto {conto} è collegato a \"{codice_voce}\", che non è una voce "
                                   "di dettaglio dello schema ordinario.", codice, codice_voce)
            continue
        if abs(saldo) < TOLLERANZA:
            continue
        if codice_voce is None:
            non_classificati.append(codice)
            avviso(ERRORE, f"Il conto {conto} ha saldo {_euro(saldo)} ma non è collegato a nessuna voce "
                           "di bilancio: l'importo resta fuori e il bilancio non quadra.", codice)
            continue

        voce = bs.VOCI_ORDINARIO[codice_voce]
        patrimoniale = bs.e_stato_patrimoniale(voce.codice)
        if tipo in ("ATTIVO", "PASSIVO") and not patrimoniale:
            avviso(ATTENZIONE, f"Il conto {conto} è di tipo {tipo} ma è collegato a una voce del conto "
                               f"economico ({_descrivi(voce.codice)}); il suo saldo verrebbe riportato "
                               "all'esercizio successivo.", codice, voce.codice)
        elif tipo in ("COSTO", "RICAVO") and patrimoniale:
            avviso(ATTENZIONE, f"Il conto {conto} è di tipo {tipo} ma è collegato a una voce dello stato "
                               f"patrimoniale ({_descrivi(voce.codice)}); il suo saldo non verrebbe "
                               "riportato all'esercizio successivo.", codice, voce.codice)

        importo = _importo(saldo, voce)
        rettifica = codice in rettifiche or (padre in rettifiche if padre else False)
        atteso = _inverti(voce.segno_atteso) if rettifica else voce.segno_atteso
        if _segno_anomalo(importo, atteso):
            lato = "Dare" if saldo > 0 else "Avere"
            alternativa = opposte.get(codice) or (opposte.get(padre) if ereditata else None)
            if alternativa and bs.voce_collegabile(alternativa):
                originale = voce
                voce = bs.VOCI_ORDINARIO[alternativa]
                importo = _importo(saldo, voce)
                avviso(INFORMAZIONE, f"Il conto {conto} ha saldo {lato} di {_euro(abs(saldo))}: è esposto in "
                                     f"{_descrivi(voce.codice)} invece che in {_descrivi(originale.codice)}.",
                       codice, voce.codice)
            elif rettifica:
                avviso(ATTENZIONE, f"Il conto di rettifica {conto} ha saldo {lato} di {_euro(abs(saldo))}, "
                                   f"dalla stessa parte della voce {_descrivi(voce.codice)} che dovrebbe "
                                   "ridurre: verificare le registrazioni.", codice, voce.codice)
            else:
                avviso(ATTENZIONE, f"Il conto {conto} ha saldo {lato} di {_euro(abs(saldo))}, opposto a quello "
                                   f"normale della voce {_descrivi(voce.codice)}, che ne risulta ridotta. Se il "
                                   "saldo indica un'altra natura (per esempio uno scoperto di conto corrente, "
                                   "che è un debito verso banche) il conto va collegato alla voce giusta o "
                                   "va indicata una voce per il saldo opposto: le partite non si compensano "
                                   "(art. 2423-ter, comma 6).", codice, voce.codice)

        if voce.codice == bs.UTILE_ESERCIZIO_SP:
            saldo_utile += importo
            avviso(ATTENZIONE, f"Il conto {conto}, collegato all'utile (perdita) dell'esercizio, ha saldo "
                               f"{_euro(saldo)}: l'importo si somma al risultato del conto economico. Se "
                               "sono già state registrate le scritture di chiusura il conto economico è "
                               "incompleto; se è il risultato di un esercizio precedente va girato a "
                               "riserve o a utili (perdite) portati a nuovo.", codice, voce.codice)

        importi[voce.codice] += importo
        conti.setdefault(voce.codice, []).append((codice, importo))

    importi = {f: round(v, 2) for f, v in importi.items()}
    return Classificazione(importi, conti, 0.0, avvisi, non_classificati, round(saldo_utile, 2))


def valuta_schema(voci, importi):
    """Importo di ogni voce di uno schema (sp o ce) dati gli importi delle foglie ordinarie."""
    indice = {v.codice: v for v in voci}
    figli = {}
    for v in voci:
        if v.padre:
            figli.setdefault(v.padre, []).append(v)
    valori = {}

    def valore(codice):
        if codice in valori:
            return valori[codice]
        v = indice[codice]
        if v.genere == bs.FOGLIA:
            x = sum(importi.get(f, 0.0) for f in _foglie(v))
        elif v.genere == bs.CALCOLATA:
            x = sum(segno * valore(c) for c, segno in v.formula)
        else:
            x = sum(f.segno * valore(f.codice) for f in figli.get(codice, ()))
        valori[codice] = round(x, 2)
        return valori[codice]

    for v in voci:
        valore(v.codice)
    return valori


def _totali_sp(importi):
    valori = valuta_schema(bs.SCHEMA_ORDINARIO_SP, importi)
    return valori[bs.ATTIVO], valori[bs.PASSIVO]


def importi_esercizio(saldi, mappa, rettifiche=(), voci_saldo_opposto=None,
                      unita_di_euro=False, esercizio=CORRENTE):
    """
    Classificazione completa di un esercizio: foglie ordinarie, risultato del conto
    economico sommato ad A.IX ed eventuale arrotondamento all'unità di euro.
    """
    c = classifica_conti(saldi, mappa, rettifiche, voci_saldo_opposto, esercizio)
    importi = dict(c.importi)
    quadrava = None
    if unita_di_euro:
        prova = dict(importi)
        prova[bs.UTILE_ESERCIZIO_SP] += valuta_schema(bs.SCHEMA_ORDINARIO_CE, prova)[bs.UTILE_ESERCIZIO_CE]
        attivo, passivo = _totali_sp(prova)
        quadrava = abs(attivo - passivo) < TOLLERANZA
        importi = {f: _arrotonda_euro(v) for f, v in importi.items()}

    risultato = valuta_schema(bs.SCHEMA_ORDINARIO_CE, importi)[bs.UTILE_ESERCIZIO_CE]
    importi[bs.UTILE_ESERCIZIO_SP] = round(importi[bs.UTILE_ESERCIZIO_SP] + risultato, 2)

    if unita_di_euro and quadrava:
        attivo, passivo = _totali_sp(importi)
        differenza = round(attivo - passivo, 2)
        if differenza:
            importi[bs.RISERVA_ARROTONDAMENTO] = round(importi[bs.RISERVA_ARROTONDAMENTO] + differenza, 2)
            c.avvisi.append(Avviso(
                INFORMAZIONE, f"Arrotondamento all'unità di euro: la differenza di {_euro(differenza)} è "
                              f"esposta in {_descrivi(bs.RISERVA_ARROTONDAMENTO)}.",
                voce=bs.RISERVA_ARROTONDAMENTO, esercizio=esercizio))
    c.importi = importi
    c.risultato = risultato
    return c


def _righe(voci, valori, valori_prec, conti_foglie):
    """Righe di un prospetto nell'ordine dello schema, con le righe di totale dopo le sottovoci."""
    figli = {}
    radici = []
    for v in voci:
        (figli.setdefault(v.padre, []) if v.padre else radici).append(v)
    righe = []

    def prec(codice):
        return None if valori_prec is None else valori_prec.get(codice, 0.0)

    def conti_di(v):
        trovati = []
        for f in _foglie(v):
            trovati.extend(conti_foglie.get(f, ()))
        return tuple(trovati)

    def visita(v, livello):
        if v.genere == bs.CALCOLATA:
            righe.append(RigaBilancio(v.codice, v.etichetta, livello, RISULTATO,
                                      valori[v.codice], prec(v.codice)))
        elif v.genere == bs.FOGLIA:
            righe.append(RigaBilancio(v.codice, v.etichetta, livello, VOCE,
                                      valori[v.codice], prec(v.codice), conti_di(v)))
        elif v.totale:
            righe.append(RigaBilancio(v.codice, v.etichetta, livello, INTESTAZIONE))
            for f in figli.get(v.codice, ()):
                visita(f, livello + 1)
            righe.append(RigaBilancio(v.codice, v.totale, livello, TOTALE,
                                      valori[v.codice], prec(v.codice)))
        else:
            righe.append(RigaBilancio(v.codice, v.etichetta, livello, VOCE,
                                      valori[v.codice], prec(v.codice)))
            for f in figli.get(v.codice, ()):
                visita(f, livello + 1)

    for v in radici:
        visita(v, 0)
    return righe


def _prospetto(schema, corrente, precedente):
    sp, ce = bs.SCHEMI[schema]
    valori = {**valuta_schema(sp, corrente.importi), **valuta_schema(ce, corrente.importi)}
    valori_prec = None
    if precedente is not None:
        valori_prec = {**valuta_schema(sp, precedente.importi), **valuta_schema(ce, precedente.importi)}
    # I conti indicati nelle righe sono quelli dell'esercizio corrente
    return Prospetto(
        schema=schema,
        titolo=bs.NOMI_SCHEMI[schema],
        stato_patrimoniale=_righe(sp, valori, valori_prec, corrente.conti),
        conto_economico=_righe(ce, valori, valori_prec, corrente.conti),
        valori=valori,
        valori_precedenti=valori_prec,
    )


def _controlli(prospetti, c, esercizio):
    """Controlli sul bilancio di un esercizio. Restituisce (quadra, avvisi)."""
    avvisi = []
    ordinario = prospetti["ordinario"]
    valori = ordinario.valori if esercizio == CORRENTE else ordinario.valori_precedenti
    attivo, passivo = valori[bs.ATTIVO], valori[bs.PASSIVO]
    differenza = round(attivo - passivo, 2)
    quadra = abs(differenza) < TOLLERANZA
    if not quadra:
        if c.non_classificati:
            causa = ("dipende dai conti con saldo che non sono classificati: "
                     + ", ".join(c.non_classificati) + ".")
        else:
            causa = ("tutti i conti con saldo sono classificati: verificare che le registrazioni "
                     "dell'esercizio siano in pareggio.")
        avvisi.append(Avviso(ERRORE, f"Il totale dell'attivo ({_euro(attivo)}) e il totale del passivo "
                                     f"({_euro(passivo)}) non coincidono: differenza {_euro(differenza)}; "
                                     + causa, esercizio=esercizio))

    # Coerenza tra gli schemi (per costruzione i totali coincidono)
    for nome in ("abbreviato", "micro"):
        altri = prospetti[nome].valori if esercizio == CORRENTE else prospetti[nome].valori_precedenti
        for codice, etichetta in ((bs.ATTIVO, "totale attivo"), (bs.PASSIVO, "totale passivo"),
                                  (bs.UTILE_ESERCIZIO_CE, "risultato dell'esercizio")):
            if abs(altri[codice] - valori[codice]) >= TOLLERANZA:
                avvisi.append(Avviso(ERRORE, f"Schema {nome}: {etichetta} {_euro(altri[codice])} diverso "
                                             f"dall'ordinario ({_euro(valori[codice])}).",
                                     voce=codice, esercizio=esercizio))

    # Voci con importo di segno anomalo
    for f in bs.FOGLIE_ORDINARIO:
        voce = bs.VOCI_ORDINARIO[f]
        importo = c.importi.get(f, 0.0)
        if f == bs.RISERVA_ARROTONDAMENTO or not _segno_anomalo(importo, voce.segno_atteso):
            continue
        avvisi.append(Avviso(ATTENZIONE, f"La voce {_descrivi(f)} ha importo {_euro(importo)}, di segno "
                                         "opposto a quello normale: le rettifiche superano il valore lordo "
                                         "oppure un conto ha il saldo dalla parte sbagliata.",
                             voce=f, esercizio=esercizio))

    # Micro-imprese: derivati e deroghe non applicabili (art. 2435-ter)
    for f, motivo in bs.VOCI_NON_APPLICABILI_MICRO.items():
        if abs(c.importi.get(f, 0.0)) >= TOLLERANZA:
            avvisi.append(Avviso(ATTENZIONE, f"La voce {_descrivi(f)} ha importo {_euro(c.importi[f])}: "
                                             f"nel bilancio delle micro-imprese di regola non c'è ({motivo}).",
                                 voce=f, esercizio=esercizio))
    return quadra, avvisi


def calcola_bilancio(saldi, mappa, saldi_precedenti=None, mappa_precedente=None, rettifiche=(),
                     voci_saldo_opposto=None, unita_di_euro=False):
    """
    Bilancio dell'esercizio nei tre schemi, con la colonna dell'esercizio
    precedente se si passano i suoi saldi.

    saldi, saldi_precedenti: righe con codice, nome, tipo, totale_dare,
        totale_avere (e padre_codice, facoltativo).
    mappa: codice del conto -> foglia dello schema ordinario.
    mappa_precedente: collegamento per l'esercizio precedente (predefinito: mappa).
    rettifiche: codici dei conti di rettifica (saldo normale opposto alla voce).
    voci_saldo_opposto: codice del conto -> voce da usare quando il saldo cambia segno.
    unita_di_euro: arrotonda le voci all'unità di euro (art. 2423, comma 6).
    """
    corrente = importi_esercizio(saldi, mappa, rettifiche, voci_saldo_opposto, unita_di_euro, CORRENTE)
    precedente = None
    if saldi_precedenti is not None:
        precedente = importi_esercizio(saldi_precedenti, mappa_precedente or mappa, rettifiche,
                                       voci_saldo_opposto, unita_di_euro, PRECEDENTE)
    prospetti = {nome: _prospetto(nome, corrente, precedente) for nome in bs.SCHEMI}

    avvisi = list(corrente.avvisi)
    quadra, controlli = _controlli(prospetti, corrente, CORRENTE)
    avvisi.extend(controlli)
    quadra_prec = None
    if precedente is not None:
        avvisi.extend(precedente.avvisi)
        quadra_prec, controlli = _controlli(prospetti, precedente, PRECEDENTE)
        avvisi.extend(controlli)
    ordine = {ERRORE: 0, ATTENZIONE: 1, INFORMAZIONE: 2}
    avvisi.sort(key=lambda a: (a.esercizio != CORRENTE, ordine[a.gravita]))

    return Bilancio(
        ordinario=prospetti["ordinario"],
        abbreviato=prospetti["abbreviato"],
        micro=prospetti["micro"],
        avvisi=avvisi,
        classificazione=corrente,
        classificazione_precedente=precedente,
        quadra=quadra,
        quadra_precedente=quadra_prec,
    )


# --- Presentazione ---

def senza_voci_nulle(righe):
    """
    Righe senza le voci a zero in entrambi gli esercizi (come d'uso, OIC 12),
    tenendo le voci con sottovoci non nulle, le righe di risultato e i totali
    dell'attivo e del passivo.
    """
    def non_nulla(r):
        return r.genere != INTESTAZIONE and bool(r.importo or r.importo_precedente)

    tieni = []
    for i, r in enumerate(righe):
        tenuta = r.genere == RISULTATO or r.livello == 0 or non_nulla(r)
        # Una voce resta se ha qualche sottovoce non nulla: le sottovoci seguono la
        # voce con un livello maggiore (le righe sono nell'ordine dello schema)
        j = i + 1
        while not tenuta and r.genere != TOTALE and j < len(righe) and righe[j].livello > r.livello:
            tenuta = non_nulla(righe[j])
            j += 1
        tieni.append(tenuta)
    # Intestazione e totale della stessa voce si tengono o si tolgono insieme
    tenute = {r.codice for r, t in zip(righe, tieni) if t and r.genere in (INTESTAZIONE, TOTALE)}
    return [r for r, t in zip(righe, tieni)
            if t or (r.genere in (INTESTAZIONE, TOTALE) and r.codice in tenute)]


def come_testo(prospetto, nulle=False, larghezza=78):
    """Il prospetto come testo a colonne (per controlli e diagnosi)."""
    con_prec = prospetto.valori_precedenti is not None

    def importo(x):
        return "" if x is None else _euro(x)

    linee = [prospetto.titolo, ""]
    for titolo, righe in (("STATO PATRIMONIALE", prospetto.stato_patrimoniale),
                          ("CONTO ECONOMICO", prospetto.conto_economico)):
        linee.append(titolo)
        for r in (righe if nulle else senza_voci_nulle(righe)):
            testo = "  " * r.livello + r.etichetta
            if len(testo) > larghezza - 32:
                testo = testo[:larghezza - 35] + "..."
            colonne = f"{importo(r.importo):>15}"
            if con_prec:
                colonne += f"{importo(r.importo_precedente):>15}"
            if r.genere == INTESTAZIONE:
                colonne = ""
            linee.append(f"{testo:<{larghezza - 30}}{colonne}")
        linee.append("")
    return "\n".join(linee)
