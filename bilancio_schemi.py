"""
Contabilino - Schemi del bilancio civilistico
Stato patrimoniale (art. 2424 c.c.) e conto economico (art. 2425 c.c.) nel testo
vigente dopo il D.Lgs. 139/2015, con le forme abbreviata (art. 2435-bis) e per le
micro-imprese (art. 2435-ter) definite come raggruppamenti delle voci ordinarie.

Il modulo contiene solo dati e funzioni di consultazione: nessun calcolo sui saldi
(quello è in bilancio.py) e nessun accesso al database.

Codici delle voci
-----------------
Ogni voce ha un codice stabile, fatto di segmenti separati da un punto che
ricalcano la numerazione del codice civile:

    SPA      stato patrimoniale, attivo          SPA.B.II.4       = Attivo B) II 4) altri beni
    SPP      stato patrimoniale, passivo         SPP.D.4.oltre    = Passivo D) 4) debiti verso banche,
    CE       conto economico                                        esigibili oltre l'esercizio successivo
                                                 CE.B.9.a         = B) 9) a) salari e stipendi
                                                 CE.C.17-bis      = C) 17-bis) utili e perdite su cambi

- lettera maiuscola della classe (A, B, C...), poi numero romano (I, II...), poi
  numero arabo con eventuale suffisso (5-bis, 11-bis, 17-bis), poi lettera minuscola
  (a, d-bis), esattamente come nel testo della legge;
- le "separate indicazioni" richieste dalla legge senza un numero proprio sono
  segmenti in parole: ".entro" e ".oltre" (scadenza dei crediti e dei debiti),
  ".richiamati"/".non_richiamati" (Attivo A), ".controllate", ".collegate",
  ".controllanti", ".sottoposte", ".altri" (rapporti di gruppo nelle voci C.15,
  C.16.a, C.16.d, C.17), il dettaglio delle Altre riserve (SPP.A.VI.*) e delle
  imposte (CE.20.*);
- la voce A.5 del conto economico è divisa in CE.A.5.a (contributi in conto
  esercizio) e CE.A.5.b (altri): le lettere sono nostre, la separata indicazione
  è della legge;
- le voci 20 e 21 del conto economico non stanno sotto una lettera: CE.20, CE.21;
- le righe di risultato intermedio sono voci calcolate: CE.A-B (differenza tra
  valore e costi della produzione) e CE.ANTE_IMPOSTE (risultato prima delle imposte).

I conti del piano dei conti si collegano alle foglie dello schema ordinario
(genere FOGLIA). Gli schemi abbreviato e micro hanno voci proprie (per esempio
SPA.B.II, SPA.C.II.oltre, CE.B.9.c-e), ognuna delle quali indica in `voci` quali
foglie dell'ordinario raggruppa: così i tre schemi derivano dagli stessi importi
e hanno per costruzione gli stessi totali.

Segni
-----
Ogni foglia dice come si ricava il suo importo dai saldi dei conti (`saldo`):
- DARE_AVERE: importo = somma(dare - avere). Attivo, costi della produzione (B),
  oneri finanziari (C.17), svalutazioni (D.19), imposte (20);
- AVERE_DARE: importo = somma(avere - dare). Passivo e patrimonio netto, valore
  della produzione (A), proventi finanziari (C.15, C.16), utili e perdite su
  cambi (C.17-bis: utile positivo, perdita negativa), rivalutazioni (D.18).

Gli importi così ottenuti sono quelli che si leggono nello schema, di norma
positivi. `segno` dice come la voce entra nel totale del padre: +1 ovunque,
tranne C.17 (-1 nel totale C: 15 + 16 - 17 ± 17-bis) e D.19 (-1 nel totale D:
18 - 19). Le sezioni A e B del conto economico non hanno padre: le combinano le
voci calcolate (CE.A-B = A - B; CE.ANTE_IMPOSTE = (A - B) + C + D; CE.21 =
CE.ANTE_IMPOSTE - 20), con i segni indicati nella loro `formula`.

`segno_atteso` dice il segno normale dell'importo: "+" (quasi tutte), "-"
(Passivo A.X, riserva negativa per azioni proprie: importo negativo) oppure "±"
(voci che per natura possono avere entrambi i segni: variazioni delle rimanenze,
utili/perdite a nuovo e d'esercizio, riserva di copertura, utili e perdite su
cambi, imposte differite e anticipate...). bilancio.py lo usa per segnalare i
conti con il saldo "dalla parte sbagliata" invece di compensarli in silenzio.

Il risultato del conto economico (CE.21) confluisce nel Passivo A.IX
(`da_risultato`): A.IX = utile (perdita) calcolato + eventuali saldi di conti
collegati ad A.IX (che di norma devono essere a zero, vedi bilancio.py).

Bilancio abbreviato (art. 2435-bis)
-----------------------------------
- Stato patrimoniale: solo le voci con lettere maiuscole e numeri romani
  (comma 2); nelle voci C.II dell'attivo e D del passivo restano separati i
  crediti e i debiti esigibili oltre l'esercizio successivo (qui come righe
  "entro" e "oltre" di C.II e di D). Le Altre riserve (A.VI) sono una voce sola.
- Conto economico: lo schema ordinario con i soli raggruppamenti consentiti dal
  comma 3: A2 e A3; B9 c), d), e); B10 a), b), c); C16 b) e c); D18 a), b), c),
  d); D19 a), b), c), d). Tutte le altre voci restano come nell'ordinario.

Bilancio delle micro-imprese (art. 2435-ter)
--------------------------------------------
Si applicano gli schemi dell'abbreviato: SCHEMA_MICRO_SP e SCHEMA_MICRO_CE sono
le stesse voci. Le differenze dell'art. 2435-ter rispetto all'abbreviato non
toccano la struttura degli schemi ma alcuni contenuti:
- non si applica l'art. 2426, comma 1, n. 11-bis (strumenti finanziari derivati
  al fair value): le voci dei derivati (Attivo B.III.4 e C.III.5, Passivo B.3,
  riserva A.VII per operazioni di copertura dei flussi finanziari attesi,
  CE D.18.d e D.19.d) di regola non hanno importi. bilancio.py li segnala se
  presenti (VOCI_NON_APPLICABILI_MICRO). Nello schema la riga A.VII resta, perché
  nel prospetto abbreviato è una voce a sé, ma deve essere a zero;
- non si applica l'art. 2423, comma 5 (deroghe in casi eccezionali): la riserva
  da deroghe (SPP.A.VI.deroghe) non dovrebbe sorgere;
- esonero da rendiconto finanziario, nota integrativa (se in calce allo stato
  patrimoniale ci sono le informazioni dell'art. 2427, primo comma, nn. 9 e 16)
  e relazione sulla gestione (se in calce ci sono quelle dell'art. 2428, nn. 3
  e 4): sono documenti fuori da questi schemi.

Limiti
------
- C.III.7 "attività finanziarie per la gestione accentrata della tesoreria" non
  è nel testo dell'art. 2424: è una voce aggiunta dal principio OIC 14 (cash
  pooling) in base all'art. 2423-ter, comma 3. È inclusa perché la usa la prassi;
  se non serve resta a zero.
- I dettagli che la legge chiede come "separata indicazione" senza dare un
  numero (Attivo A richiamato, rapporti di gruppo in C.15/16/17, Altre riserve,
  imposte correnti/differite e anticipate) sono foglie a sé con etichette
  ricalcate sulla tassonomia XBRL di uso comune, ma i loro codici non sono quelli
  della tassonomia. Il dettaglio di A.VI non è un elenco chiuso: "varie altre
  riserve" raccoglie le altre.
- La separata indicazione delle immobilizzazioni "concesse in locazione
  finanziaria" (Attivo B, riguarda il concedente) non ha voci proprie.
- Nell'abbreviato la legge permette di comprendere le voci A e D dell'attivo nella
  C.II e la voce E del passivo nella D: è una facoltà e qui non è applicata (le
  voci restano separate, il che è sempre consentito).
- I conti d'ordine non esistono più dopo il D.Lgs. 139/2015 (impegni e garanzie
  vanno in nota integrativa): non sono negli schemi.
- I limiti dimensionali (LIMITI_ABBREVIATO, LIMITI_MICRO) sono quelli aggiornati
  dal D.Lgs. 125/2024; il superamento va valutato sul primo esercizio o su due
  esercizi consecutivi e sul numero medio dei dipendenti, che il programma non
  conosce: le costanti sono solo un riferimento, nessuna funzione decide da sola
  quale forma spetta.
"""

from dataclasses import dataclass, replace
from fnmatch import fnmatchcase

# Genere della voce
SEZIONE = "sezione"      # attivo, passivo, sezioni A-D del conto economico
GRUPPO = "gruppo"        # voce con sottovoci: il suo importo è la somma dei figli
FOGLIA = "foglia"        # voce a cui si collegano i conti (o, negli schemi derivati, che raggruppa foglie)
CALCOLATA = "calcolata"  # riga di risultato: combinazione di altre voci (formula)

# Come si ricava l'importo di una foglia dai saldi dei conti
DARE_AVERE = "dare-avere"  # attivo, costi e oneri
AVERE_DARE = "avere-dare"  # passivo, ricavi e proventi

# Codici delle voci speciali
UTILE_ESERCIZIO_SP = "SPP.A.IX"
UTILE_ESERCIZIO_CE = "CE.21"
RISERVA_ARROTONDAMENTO = "SPP.A.VI.arrotondamento"

ATTIVO = "SPA"
PASSIVO = "SPP"

# Limiti dimensionali (D.Lgs. 125/2024): non vanno superati due su tre,
# nel primo esercizio o per due esercizi consecutivi
LIMITI_ABBREVIATO = {"totale_attivo": 5_500_000, "ricavi": 11_000_000, "dipendenti_medi": 50}
LIMITI_MICRO = {"totale_attivo": 220_000, "ricavi": 440_000, "dipendenti_medi": 5}


@dataclass(frozen=True)
class Voce:
    codice: str
    etichetta: str
    padre: str = None
    genere: str = FOGLIA
    saldo: str = None          # FOGLIA: DARE_AVERE o AVERE_DARE
    segno: int = 1             # come entra nel totale del padre (+1 o -1)
    segno_atteso: str = "+"    # "+", "-" oppure "±"
    totale: str = None         # SEZIONE/GRUPPO: etichetta della riga di totale (None = importo sulla riga della voce)
    formula: tuple = ()        # CALCOLATA: ((codice, segno), ...)
    voci: tuple = ()           # FOGLIA: foglie dell'ordinario raggruppate (motivi glob, vedi corrisponde)
    da_risultato: str = None   # Passivo A.IX: voce calcolata del conto economico che vi confluisce
    nota: str = ""


class _Schema:
    """Raccoglie le voci nell'ordine di esposizione (ogni padre prima dei figli)."""

    def __init__(self):
        self.voci = []

    def sezione(self, codice, etichetta, padre=None, **opzioni):
        self.voci.append(Voce(codice, etichetta, padre, SEZIONE, **opzioni))
        return codice

    def gruppo(self, codice, etichetta, padre, **opzioni):
        self.voci.append(Voce(codice, etichetta, padre, GRUPPO, **opzioni))
        return codice

    def foglia(self, codice, etichetta, padre, saldo, **opzioni):
        opzioni.setdefault("voci", (codice,))
        self.voci.append(Voce(codice, etichetta, padre, FOGLIA, saldo, **opzioni))
        return codice

    def calcolata(self, codice, etichetta, formula, **opzioni):
        self.voci.append(Voce(codice, etichetta, None, CALCOLATA, formula=tuple(formula), **opzioni))
        return codice

    def con_scadenza(self, codice, etichetta, padre, saldo, **opzioni):
        """Credito o debito con la separata indicazione della scadenza: gruppo con foglie entro/oltre."""
        self.gruppo(codice, etichetta, padre)
        self.foglia(codice + ".entro", "esigibili entro l'esercizio successivo", codice, saldo, **opzioni)
        self.foglia(codice + ".oltre", "esigibili oltre l'esercizio successivo", codice, saldo, **opzioni)
        return codice

    def per_rapporto(self, codice, etichetta, padre, saldo, preposizione, **opzioni):
        """Voce con la separata indicazione dei rapporti di gruppo (C.15, C.16.a, C.16.d, C.17)."""
        self.gruppo(codice, etichetta, padre, **opzioni)
        for chiave, nome in _RAPPORTI:
            testo = f"{preposizione} {nome}" if nome else "altri"
            self.foglia(f"{codice}.{chiave}", testo, codice, saldo)
        return codice


_RAPPORTI = (
    ("controllate", "imprese controllate"),
    ("collegate", "imprese collegate"),
    ("controllanti", "imprese controllanti"),
    ("sottoposte", "imprese sottoposte al controllo delle controllanti"),
    ("altri", None),
)


# --- Stato patrimoniale ordinario (art. 2424) ---

def _stato_patrimoniale():
    s = _Schema()
    D = DARE_AVERE
    A = AVERE_DARE

    # ATTIVO
    att = s.sezione("SPA", "ATTIVO", totale="TOTALE ATTIVO")

    s.gruppo("SPA.A", "A) Crediti verso soci per versamenti ancora dovuti, "
                      "con separata indicazione della parte già richiamata", att)
    s.foglia("SPA.A.richiamati", "parte già richiamata", "SPA.A", D)
    s.foglia("SPA.A.non_richiamati", "parte da richiamare", "SPA.A", D)

    b = s.gruppo("SPA.B", "B) Immobilizzazioni, con separata indicazione di quelle "
                          "concesse in locazione finanziaria", att,
                 totale="Totale immobilizzazioni (B)")
    bi = s.gruppo("SPA.B.I", "I - Immobilizzazioni immateriali", b,
                  totale="Totale immobilizzazioni immateriali")
    for numero, etichetta in (
        ("1", "costi di impianto e di ampliamento"),
        ("2", "costi di sviluppo"),
        ("3", "diritti di brevetto industriale e diritti di utilizzazione delle opere dell'ingegno"),
        ("4", "concessioni, licenze, marchi e diritti simili"),
        ("5", "avviamento"),
        ("6", "immobilizzazioni in corso e acconti"),
        ("7", "altre"),
    ):
        s.foglia(f"{bi}.{numero}", f"{numero}) {etichetta}", bi, D)

    bii = s.gruppo("SPA.B.II", "II - Immobilizzazioni materiali", b,
                   totale="Totale immobilizzazioni materiali")
    for numero, etichetta in (
        ("1", "terreni e fabbricati"),
        ("2", "impianti e macchinario"),
        ("3", "attrezzature industriali e commerciali"),
        ("4", "altri beni"),
        ("5", "immobilizzazioni in corso e acconti"),
    ):
        s.foglia(f"{bii}.{numero}", f"{numero}) {etichetta}", bii, D)

    biii = s.gruppo("SPA.B.III", "III - Immobilizzazioni finanziarie, con separata indicazione, "
                                 "per ciascuna voce dei crediti, degli importi esigibili entro "
                                 "l'esercizio successivo", b,
                    totale="Totale immobilizzazioni finanziarie")
    part = s.gruppo("SPA.B.III.1", "1) partecipazioni in:", biii)
    for lettera, etichetta in (
        ("a", "imprese controllate"),
        ("b", "imprese collegate"),
        ("c", "imprese controllanti"),
        ("d", "imprese sottoposte al controllo delle controllanti"),
        ("d-bis", "altre imprese"),
    ):
        s.foglia(f"{part}.{lettera}", f"{lettera}) {etichetta}", part, D)
    cred = s.gruppo("SPA.B.III.2", "2) crediti:", biii)
    for lettera, etichetta in (
        ("a", "verso imprese controllate"),
        ("b", "verso imprese collegate"),
        ("c", "verso controllanti"),
        ("d", "verso imprese sottoposte al controllo delle controllanti"),
        ("d-bis", "verso altri"),
    ):
        s.con_scadenza(f"{cred}.{lettera}", f"{lettera}) {etichetta}", cred, D)
    s.foglia("SPA.B.III.3", "3) altri titoli", biii, D)
    s.foglia("SPA.B.III.4", "4) strumenti finanziari derivati attivi", biii, D)

    c = s.gruppo("SPA.C", "C) Attivo circolante", att, totale="Totale attivo circolante (C)")
    ci = s.gruppo("SPA.C.I", "I - Rimanenze", c, totale="Totale rimanenze")
    for numero, etichetta in (
        ("1", "materie prime, sussidiarie e di consumo"),
        ("2", "prodotti in corso di lavorazione e semilavorati"),
        ("3", "lavori in corso su ordinazione"),
        ("4", "prodotti finiti e merci"),
        ("5", "acconti"),
    ):
        s.foglia(f"{ci}.{numero}", f"{numero}) {etichetta}", ci, D)

    cii = s.gruppo("SPA.C.II", "II - Crediti, con separata indicazione, per ciascuna voce, "
                               "degli importi esigibili oltre l'esercizio successivo", c,
                   totale="Totale crediti")
    for numero, etichetta in (
        ("1", "verso clienti"),
        ("2", "verso imprese controllate"),
        ("3", "verso imprese collegate"),
        ("4", "verso controllanti"),
        ("5", "verso imprese sottoposte al controllo delle controllanti"),
        ("5-bis", "crediti tributari"),
        ("5-ter", "imposte anticipate"),
        ("5-quater", "verso altri"),
    ):
        s.con_scadenza(f"{cii}.{numero}", f"{numero}) {etichetta}", cii, D)

    ciii = s.gruppo("SPA.C.III", "III - Attività finanziarie che non costituiscono immobilizzazioni", c,
                    totale="Totale attività finanziarie che non costituiscono immobilizzazioni")
    for numero, etichetta in (
        ("1", "partecipazioni in imprese controllate"),
        ("2", "partecipazioni in imprese collegate"),
        ("3", "partecipazioni in imprese controllanti"),
        ("3-bis", "partecipazioni in imprese sottoposte al controllo delle controllanti"),
        ("4", "altre partecipazioni"),
        ("5", "strumenti finanziari derivati attivi"),
        ("6", "altri titoli"),
    ):
        s.foglia(f"{ciii}.{numero}", f"{numero}) {etichetta}", ciii, D)
    s.foglia("SPA.C.III.7", "7) attività finanziarie per la gestione accentrata della tesoreria", ciii, D,
             nota="Voce prevista dal principio OIC 14 (art. 2423-ter, comma 3), non dal testo dell'art. 2424.")

    civ = s.gruppo("SPA.C.IV", "IV - Disponibilità liquide", c, totale="Totale disponibilità liquide")
    for numero, etichetta in (
        ("1", "depositi bancari e postali"),
        ("2", "assegni"),
        ("3", "danaro e valori in cassa"),
    ):
        s.foglia(f"{civ}.{numero}", f"{numero}) {etichetta}", civ, D)

    s.foglia("SPA.D", "D) Ratei e risconti", att, D)

    # PASSIVO
    pas = s.sezione("SPP", "PASSIVO", totale="TOTALE PASSIVO")

    pn = s.gruppo("SPP.A", "A) Patrimonio netto", pas, totale="Totale patrimonio netto")
    s.foglia("SPP.A.I", "I - Capitale", pn, A)
    s.foglia("SPP.A.II", "II - Riserva da soprapprezzo delle azioni", pn, A)
    s.foglia("SPP.A.III", "III - Riserve di rivalutazione", pn, A)
    s.foglia("SPP.A.IV", "IV - Riserva legale", pn, A)
    s.foglia("SPP.A.V", "V - Riserve statutarie", pn, A)
    vi = s.gruppo("SPP.A.VI", "VI - Altre riserve, distintamente indicate", pn)
    for chiave, etichetta, atteso in (
        ("straordinaria", "Riserva straordinaria", "+"),
        ("versamenti_capitale", "Versamenti in conto capitale", "+"),
        ("versamenti_futuro_aumento", "Versamenti in conto futuro aumento di capitale", "+"),
        ("versamenti_copertura_perdite", "Versamenti a copertura perdite", "+"),
        ("utili_cambi", "Riserva per utili su cambi non realizzati", "+"),
        ("deroghe", "Riserva da deroghe ex art. 2423, comma 5, c.c.", "+"),
        ("arrotondamento", "Riserva da differenza di arrotondamento all'unità di euro", "±"),
        ("varie", "Varie altre riserve", "±"),
    ):
        s.foglia(f"{vi}.{chiave}", etichetta, vi, A, segno_atteso=atteso)
    s.foglia("SPP.A.VII", "VII - Riserva per operazioni di copertura dei flussi finanziari attesi",
             pn, A, segno_atteso="±")
    s.foglia("SPP.A.VIII", "VIII - Utili (perdite) portati a nuovo", pn, A, segno_atteso="±")
    s.foglia(UTILE_ESERCIZIO_SP, "IX - Utile (perdita) dell'esercizio", pn, A, segno_atteso="±",
             da_risultato=UTILE_ESERCIZIO_CE,
             nota="Riceve il risultato del conto economico (voce 21).")
    s.foglia("SPP.A.X", "X - Riserva negativa per azioni proprie in portafoglio", pn, A, segno_atteso="-",
             nota="Riserva negativa (art. 2357-ter c.c.): importo negativo.")

    fondi = s.gruppo("SPP.B", "B) Fondi per rischi e oneri", pas, totale="Totale fondi per rischi ed oneri")
    for numero, etichetta in (
        ("1", "per trattamento di quiescenza e obblighi simili"),
        ("2", "per imposte, anche differite"),
        ("3", "strumenti finanziari derivati passivi"),
        ("4", "altri"),
    ):
        s.foglia(f"{fondi}.{numero}", f"{numero}) {etichetta}", fondi, A)

    s.foglia("SPP.C", "C) Trattamento di fine rapporto di lavoro subordinato", pas, A)

    deb = s.gruppo("SPP.D", "D) Debiti, con separata indicazione, per ciascuna voce, degli importi "
                            "esigibili oltre l'esercizio successivo", pas, totale="Totale debiti")
    for numero, etichetta in (
        ("1", "obbligazioni"),
        ("2", "obbligazioni convertibili"),
        ("3", "debiti verso soci per finanziamenti"),
        ("4", "debiti verso banche"),
        ("5", "debiti verso altri finanziatori"),
        ("6", "acconti"),
        ("7", "debiti verso fornitori"),
        ("8", "debiti rappresentati da titoli di credito"),
        ("9", "debiti verso imprese controllate"),
        ("10", "debiti verso imprese collegate"),
        ("11", "debiti verso controllanti"),
        ("11-bis", "debiti verso imprese sottoposte al controllo delle controllanti"),
        ("12", "debiti tributari"),
        ("13", "debiti verso istituti di previdenza e di sicurezza sociale"),
        ("14", "altri debiti"),
    ):
        s.con_scadenza(f"{deb}.{numero}", f"{numero}) {etichetta}", deb, A)

    s.foglia("SPP.E", "E) Ratei e risconti", pas, A)
    return tuple(s.voci)


# --- Conto economico ordinario (art. 2425) ---

def _conto_economico():
    s = _Schema()
    D = DARE_AVERE
    A = AVERE_DARE

    va = s.sezione("CE.A", "A) Valore della produzione", totale="Totale valore della produzione")
    s.foglia("CE.A.1", "1) ricavi delle vendite e delle prestazioni", va, A)
    s.foglia("CE.A.2", "2) variazioni delle rimanenze di prodotti in corso di lavorazione, "
                       "semilavorati e finiti", va, A, segno_atteso="±")
    s.foglia("CE.A.3", "3) variazioni dei lavori in corso su ordinazione", va, A, segno_atteso="±")
    s.foglia("CE.A.4", "4) incrementi di immobilizzazioni per lavori interni", va, A)
    a5 = s.gruppo("CE.A.5", "5) altri ricavi e proventi, con separata indicazione dei contributi "
                            "in conto esercizio", va)
    s.foglia("CE.A.5.a", "contributi in conto esercizio", a5, A)
    s.foglia("CE.A.5.b", "altri", a5, A)

    cp = s.sezione("CE.B", "B) Costi della produzione", totale="Totale costi della produzione")
    s.foglia("CE.B.6", "6) per materie prime, sussidiarie, di consumo e di merci", cp, D)
    s.foglia("CE.B.7", "7) per servizi", cp, D)
    s.foglia("CE.B.8", "8) per godimento di beni di terzi", cp, D)
    b9 = s.gruppo("CE.B.9", "9) per il personale:", cp)
    for lettera, etichetta in (
        ("a", "salari e stipendi"),
        ("b", "oneri sociali"),
        ("c", "trattamento di fine rapporto"),
        ("d", "trattamento di quiescenza e simili"),
        ("e", "altri costi"),
    ):
        s.foglia(f"{b9}.{lettera}", f"{lettera}) {etichetta}", b9, D)
    b10 = s.gruppo("CE.B.10", "10) ammortamenti e svalutazioni:", cp)
    for lettera, etichetta in (
        ("a", "ammortamento delle immobilizzazioni immateriali"),
        ("b", "ammortamento delle immobilizzazioni materiali"),
        ("c", "altre svalutazioni delle immobilizzazioni"),
        ("d", "svalutazioni dei crediti compresi nell'attivo circolante e delle disponibilità liquide"),
    ):
        s.foglia(f"{b10}.{lettera}", f"{lettera}) {etichetta}", b10, D)
    s.foglia("CE.B.11", "11) variazioni delle rimanenze di materie prime, sussidiarie, di consumo e merci",
             cp, D, segno_atteso="±",
             nota="Rimanenze iniziali meno rimanenze finali: positivo se il magazzino diminuisce.")
    s.foglia("CE.B.12", "12) accantonamenti per rischi", cp, D)
    s.foglia("CE.B.13", "13) altri accantonamenti", cp, D)
    s.foglia("CE.B.14", "14) oneri diversi di gestione", cp, D)

    s.calcolata("CE.A-B", "Differenza tra valore e costi della produzione (A - B)",
                (("CE.A", 1), ("CE.B", -1)))

    pf = s.sezione("CE.C", "C) Proventi e oneri finanziari",
                   totale="Totale proventi e oneri finanziari (15 + 16 - 17 ± 17-bis)")
    s.per_rapporto("CE.C.15", "15) proventi da partecipazioni, con separata indicazione di quelli "
                              "relativi ad imprese controllate e collegate e di quelli relativi a "
                              "controllanti e a imprese sottoposte al controllo di queste ultime",
                   pf, A, "da")
    c16 = s.gruppo("CE.C.16", "16) altri proventi finanziari:", pf)
    s.per_rapporto("CE.C.16.a", "a) da crediti iscritti nelle immobilizzazioni, con separata indicazione "
                                "di quelli da imprese controllate e collegate e di quelli da controllanti "
                                "e da imprese sottoposte al controllo di queste ultime", c16, A, "da")
    s.foglia("CE.C.16.b", "b) da titoli iscritti nelle immobilizzazioni che non costituiscono "
                          "partecipazioni", c16, A)
    s.foglia("CE.C.16.c", "c) da titoli iscritti nell'attivo circolante che non costituiscono "
                          "partecipazioni", c16, A)
    s.per_rapporto("CE.C.16.d", "d) proventi diversi dai precedenti, con separata indicazione di quelli "
                                "da imprese controllate e collegate e di quelli da controllanti e da "
                                "imprese sottoposte al controllo di queste ultime", c16, A, "da")
    s.per_rapporto("CE.C.17", "17) interessi e altri oneri finanziari, con separata indicazione di quelli "
                              "verso imprese controllate e collegate e verso controllanti e verso imprese "
                              "sottoposte al controllo di queste ultime", pf, D, "verso", segno=-1)
    s.foglia("CE.C.17-bis", "17-bis) utili e perdite su cambi", pf, A, segno_atteso="±",
             nota="Utili positivi, perdite negative: entra con il proprio segno nel totale C.")

    rv = s.sezione("CE.D", "D) Rettifiche di valore di attività e passività finanziarie",
                   totale="Totale delle rettifiche di valore di attività e passività finanziarie (18 - 19)")
    d18 = s.gruppo("CE.D.18", "18) rivalutazioni:", rv)
    for lettera, etichetta in (
        ("a", "di partecipazioni"),
        ("b", "di immobilizzazioni finanziarie che non costituiscono partecipazioni"),
        ("c", "di titoli iscritti all'attivo circolante che non costituiscono partecipazioni"),
        ("d", "di strumenti finanziari derivati"),
    ):
        s.foglia(f"{d18}.{lettera}", f"{lettera}) {etichetta}", d18, A)
    d19 = s.gruppo("CE.D.19", "19) svalutazioni:", rv, segno=-1)
    for lettera, etichetta in (
        ("a", "di partecipazioni"),
        ("b", "di immobilizzazioni finanziarie che non costituiscono partecipazioni"),
        ("c", "di titoli iscritti nell'attivo circolante che non costituiscono partecipazioni"),
        ("d", "di strumenti finanziari derivati"),
    ):
        s.foglia(f"{d19}.{lettera}", f"{lettera}) {etichetta}", d19, D)

    s.calcolata("CE.ANTE_IMPOSTE", "Risultato prima delle imposte (A - B ± C ± D)",
                (("CE.A-B", 1), ("CE.C", 1), ("CE.D", 1)))

    imp = s.gruppo("CE.20", "20) imposte sul reddito dell'esercizio, correnti, differite e anticipate", None)
    s.foglia("CE.20.correnti", "imposte correnti", imp, D)
    s.foglia("CE.20.precedenti", "imposte relative a esercizi precedenti", imp, D, segno_atteso="±")
    s.foglia("CE.20.differite_anticipate", "imposte differite e anticipate", imp, D, segno_atteso="±",
             nota="Differite positive, anticipate negative (riducono le imposte).")
    s.foglia("CE.20.consolidato", "proventi (oneri) da adesione al regime di consolidato fiscale / "
                                  "trasparenza fiscale", imp, D, segno_atteso="±")

    s.calcolata(UTILE_ESERCIZIO_CE, "21) utile (perdita) dell'esercizio",
                (("CE.ANTE_IMPOSTE", 1), ("CE.20", -1)))
    return tuple(s.voci)


SCHEMA_ORDINARIO_SP = _stato_patrimoniale()
SCHEMA_ORDINARIO_CE = _conto_economico()
VOCI_ORDINARIO = {v.codice: v for v in SCHEMA_ORDINARIO_SP + SCHEMA_ORDINARIO_CE}
FOGLIE_ORDINARIO = tuple(v.codice for v in SCHEMA_ORDINARIO_SP + SCHEMA_ORDINARIO_CE if v.genere == FOGLIA)


# --- Stato patrimoniale abbreviato (art. 2435-bis, comma 2) ---

def _stato_patrimoniale_abbreviato():
    s = _Schema()
    D = DARE_AVERE
    A = AVERE_DARE
    o = VOCI_ORDINARIO

    def foglia(codice, padre, saldo, voci=None, etichetta=None, **opzioni):
        """Voce dell'abbreviato con l'etichetta della corrispondente voce ordinaria."""
        s.foglia(codice, etichetta or o[codice].etichetta, padre, saldo, voci=voci or (codice,), **opzioni)

    att = s.sezione("SPA", "ATTIVO", totale="TOTALE ATTIVO")
    s.gruppo("SPA.A", o["SPA.A"].etichetta, att)
    foglia("SPA.A.richiamati", "SPA.A", D)
    foglia("SPA.A.non_richiamati", "SPA.A", D)
    s.gruppo("SPA.B", "B) Immobilizzazioni", att, totale="Totale immobilizzazioni (B)")
    foglia("SPA.B.I", "SPA.B", D)
    foglia("SPA.B.II", "SPA.B", D)
    foglia("SPA.B.III", "SPA.B", D, etichetta="III - Immobilizzazioni finanziarie")
    s.gruppo("SPA.C", "C) Attivo circolante", att, totale="Totale attivo circolante (C)")
    foglia("SPA.C.I", "SPA.C", D)
    s.gruppo("SPA.C.II", "II - Crediti", "SPA.C", totale="Totale crediti")
    foglia("SPA.C.II.entro", "SPA.C.II", D, voci=("SPA.C.II.*.entro",),
           etichetta="esigibili entro l'esercizio successivo")
    foglia("SPA.C.II.oltre", "SPA.C.II", D, voci=("SPA.C.II.*.oltre",),
           etichetta="esigibili oltre l'esercizio successivo")
    foglia("SPA.C.III", "SPA.C", D)
    foglia("SPA.C.IV", "SPA.C", D)
    foglia("SPA.D", att, D)

    pas = s.sezione("SPP", "PASSIVO", totale="TOTALE PASSIVO")
    s.gruppo("SPP.A", "A) Patrimonio netto", pas, totale="Totale patrimonio netto")
    for numero in ("I", "II", "III", "IV", "V"):
        foglia(f"SPP.A.{numero}", "SPP.A", A)
    foglia("SPP.A.VI", "SPP.A", A, etichetta="VI - Altre riserve", segno_atteso="±")
    for numero in ("VII", "VIII", "IX", "X"):
        v = o[f"SPP.A.{numero}"]
        foglia(v.codice, "SPP.A", A, segno_atteso=v.segno_atteso, nota=v.nota)
    foglia("SPP.B", pas, A, etichetta="B) Fondi per rischi e oneri")
    foglia("SPP.C", pas, A)
    s.gruppo("SPP.D", "D) Debiti", pas, totale="Totale debiti")
    foglia("SPP.D.entro", "SPP.D", A, voci=("SPP.D.*.entro",),
           etichetta="esigibili entro l'esercizio successivo")
    foglia("SPP.D.oltre", "SPP.D", A, voci=("SPP.D.*.oltre",),
           etichetta="esigibili oltre l'esercizio successivo")
    foglia("SPP.E", pas, A)
    return tuple(s.voci)


# --- Conto economico abbreviato (art. 2435-bis, comma 3) ---

# (codice della voce raggruppata, etichetta, foglie dell'ordinario raggruppate).
# Se il codice è quello del gruppo ordinario (18, 19), il gruppo diventa una voce unica.
RAGGRUPPAMENTI_CE_ABBREVIATO = (
    ("CE.A.2-3", "2) e 3) variazioni delle rimanenze di prodotti in corso di lavorazione, semilavorati "
                 "e finiti e dei lavori in corso su ordinazione", ("CE.A.2", "CE.A.3")),
    ("CE.B.9.c-e", "c), d), e) trattamento di fine rapporto, trattamento di quiescenza e simili, "
                   "altri costi", ("CE.B.9.c", "CE.B.9.d", "CE.B.9.e")),
    ("CE.B.10.a-c", "a), b), c) ammortamento delle immobilizzazioni immateriali e materiali, "
                    "altre svalutazioni delle immobilizzazioni", ("CE.B.10.a", "CE.B.10.b", "CE.B.10.c")),
    ("CE.C.16.b-c", "b), c) da titoli iscritti nelle immobilizzazioni e nell'attivo circolante che "
                    "non costituiscono partecipazioni", ("CE.C.16.b", "CE.C.16.c")),
    ("CE.D.18", "18) rivalutazioni", ("CE.D.18.a", "CE.D.18.b", "CE.D.18.c", "CE.D.18.d")),
    ("CE.D.19", "19) svalutazioni", ("CE.D.19.a", "CE.D.19.b", "CE.D.19.c", "CE.D.19.d")),
)


def _deriva_conto_economico(voci, raggruppamenti):
    """Schema ordinario con le foglie indicate sostituite da una voce che le raggruppa."""
    indice = {v.codice: v for v in voci}
    membri = {m: r for r in raggruppamenti for m in r[2]}
    gruppi_unificati = {r[0]: r for r in raggruppamenti if r[0] in indice}
    risultato = []
    emessi = set()
    for v in voci:
        if v.padre in gruppi_unificati:
            continue  # sottovoce di un gruppo diventato voce unica
        if v.codice in gruppi_unificati:
            codice, etichetta, foglie = gruppi_unificati[v.codice]
            risultato.append(replace(v, etichetta=etichetta, genere=FOGLIA, voci=foglie, totale=None,
                                     saldo=indice[foglie[0]].saldo,
                                     segno_atteso=_segno_comune(indice[f] for f in foglie)))
            continue
        r = membri.get(v.codice)
        if r is None:
            risultato.append(v)
        elif r[0] not in emessi:
            emessi.add(r[0])
            foglie = [indice[f] for f in r[2]]
            risultato.append(Voce(r[0], r[1], v.padre, FOGLIA, v.saldo, segno=v.segno,
                                  segno_atteso=_segno_comune(foglie), voci=r[2]))
    return tuple(risultato)


def _segno_comune(voci):
    segni = {v.segno_atteso for v in voci}
    return segni.pop() if len(segni) == 1 else "±"


SCHEMA_ABBREVIATO_SP = _stato_patrimoniale_abbreviato()
SCHEMA_ABBREVIATO_CE = _deriva_conto_economico(SCHEMA_ORDINARIO_CE, RAGGRUPPAMENTI_CE_ABBREVIATO)

# Micro-imprese (art. 2435-ter): gli stessi schemi dell'abbreviato
SCHEMA_MICRO_SP = SCHEMA_ABBREVIATO_SP
SCHEMA_MICRO_CE = SCHEMA_ABBREVIATO_CE

# Voci dell'ordinario che nelle micro-imprese di regola restano a zero:
# l'art. 2435-ter esclude l'art. 2426, comma 1, n. 11-bis (derivati al fair value)
VOCI_NON_APPLICABILI_MICRO = {
    "SPA.B.III.4": "strumenti finanziari derivati attivi (art. 2426, n. 11-bis non applicabile)",
    "SPA.C.III.5": "strumenti finanziari derivati attivi (art. 2426, n. 11-bis non applicabile)",
    "SPP.A.VII": "riserva per operazioni di copertura dei flussi finanziari attesi "
                 "(art. 2426, n. 11-bis non applicabile)",
    "SPP.B.3": "strumenti finanziari derivati passivi (art. 2426, n. 11-bis non applicabile)",
    "CE.D.18.d": "rivalutazioni di strumenti finanziari derivati (art. 2426, n. 11-bis non applicabile)",
    "CE.D.19.d": "svalutazioni di strumenti finanziari derivati (art. 2426, n. 11-bis non applicabile)",
    "SPP.A.VI.deroghe": "riserva da deroghe (art. 2423, comma 5, non applicabile)",
}

SCHEMI = {
    "ordinario": (SCHEMA_ORDINARIO_SP, SCHEMA_ORDINARIO_CE),
    "abbreviato": (SCHEMA_ABBREVIATO_SP, SCHEMA_ABBREVIATO_CE),
    "micro": (SCHEMA_MICRO_SP, SCHEMA_MICRO_CE),
}
NOMI_SCHEMI = {
    "ordinario": "Bilancio ordinario (artt. 2424 e 2425 c.c.)",
    "abbreviato": "Bilancio in forma abbreviata (art. 2435-bis c.c.)",
    "micro": "Bilancio delle micro-imprese (art. 2435-ter c.c.)",
}


# --- Consultazione ---

def corrisponde(codice_foglia, motivo):
    """
    Vero se la foglia dell'ordinario rientra nel motivo di una voce raggruppata:
    il motivo indica una voce e tutte le sue sottovoci ("SPA.B.II" comprende
    "SPA.B.II.4") e può contenere * ("SPA.C.II.*.oltre").
    """
    return fnmatchcase(codice_foglia, motivo) or fnmatchcase(codice_foglia, motivo + ".*")


def foglie_di(voce):
    """Foglie dell'ordinario raggruppate da una voce FOGLIA di qualsiasi schema."""
    return [f for f in FOGLIE_ORDINARIO if any(corrisponde(f, m) for m in voce.voci)]


def e_stato_patrimoniale(codice):
    return codice.startswith(("SPA", "SPP"))


def e_conto_economico(codice):
    return codice.startswith("CE.")


def voce_collegabile(codice):
    """Vero se un conto si può collegare a questa voce (foglia dello schema ordinario)."""
    v = VOCI_ORDINARIO.get(codice)
    return v is not None and v.genere == FOGLIA


def percorso(codice, separatore=" > "):
    """Etichetta completa della voce ordinaria, dai livelli superiori ("PASSIVO > D) Debiti... > ...")."""
    parti = []
    v = VOCI_ORDINARIO.get(codice)
    while v is not None:
        parti.append(v.etichetta)
        v = VOCI_ORDINARIO.get(v.padre) if v.padre else None
    return separatore.join(reversed(parti))


def voci_collegabili():
    """Lista (codice, percorso) delle foglie dell'ordinario, nell'ordine dello schema: per scegliere la voce di un conto."""
    return [(c, percorso(c)) for c in FOGLIE_ORDINARIO]


def verifica_schemi():
    """
    Controlli di coerenza degli schemi (per i test): codici unici, padri esistenti
    e dichiarati prima dei figli, formule valide, foglie con il verso del saldo, e
    in ogni schema derivato ciascuna foglia dell'ordinario raggruppata da una e
    una sola voce. Restituisce la lista dei problemi (vuota se tutto è in ordine).
    """
    problemi = []
    for nome, (sp, ce) in SCHEMI.items():
        visti = set()
        for v in sp + ce:
            if v.codice in visti:
                problemi.append(f"{nome}: codice duplicato {v.codice}")
            if v.padre and v.padre not in visti:
                problemi.append(f"{nome}: {v.codice} ha il padre {v.padre} mancante o dichiarato dopo")
            visti.add(v.codice)
            if v.genere == FOGLIA and v.saldo not in (DARE_AVERE, AVERE_DARE):
                problemi.append(f"{nome}: la foglia {v.codice} non dice il verso del saldo")
            if v.segno not in (1, -1) or v.segno_atteso not in ("+", "-", "±"):
                problemi.append(f"{nome}: segni non validi in {v.codice}")
        for v in sp + ce:
            for codice, segno in v.formula:
                if codice not in visti or segno not in (1, -1):
                    problemi.append(f"{nome}: formula di {v.codice} non valida ({codice})")
        for parte, voci in (("SP", sp), ("CE", ce)):
            ordinarie = [f for f in FOGLIE_ORDINARIO if e_stato_patrimoniale(f) == (parte == "SP")]
            conteggio = {f: [] for f in ordinarie}
            for v in voci:
                if v.genere != FOGLIA:
                    continue
                trovate = foglie_di(v)
                if not trovate:
                    problemi.append(f"{nome}: la voce {v.codice} non raggruppa nessuna foglia")
                for f in trovate:
                    if f not in conteggio:
                        problemi.append(f"{nome}: la voce {v.codice} raggruppa {f} dell'altro prospetto")
                    else:
                        conteggio[f].append(v.codice)
                        if VOCI_ORDINARIO[f].saldo != v.saldo:
                            problemi.append(f"{nome}: {v.codice} raggruppa {f} con verso del saldo diverso")
            for f, chi in conteggio.items():
                if len(chi) != 1:
                    problemi.append(f"{nome}: la foglia {f} è raggruppata da {len(chi)} voci {chi}")
    return problemi
