"""
Contabilino - Piano dei conti di base
Piano dei conti per una piccola impresa in contabilità ordinaria (s.r.l. o ditta
individuale), con i conti per la gestione dell'IVA, da proporre quando si crea
un nuovo archivio.

Struttura
---------
- due livelli, come nel resto del programma: conto (padre) e sottoconti;
- codici di quattro cifre, così l'ordine alfabetico coincide con quello
  numerico: il padre finisce con 00 ("2200"), i sottoconti ne prendono le prime
  due cifre ("2201", "2202"...). La prima cifra indica la classe:
      1 immobilizzazioni e relativi fondi    5 valore della produzione e proventi
      2 attivo circolante e ratei attivi     6 costi della produzione e oneri finanziari
      3 patrimonio netto                     7 imposte sul reddito
      4 fondi, TFR, debiti e ratei passivi
- ogni sottoconto è collegato a una foglia dello schema ordinario di
  bilancio_schemi (MAPPA). Anche i conti padre hanno una voce quando ce n'è una
  naturale: vale per gli eventuali movimenti registrati sul padre e per i
  sottoconti che l'utente aggiunge senza collegarli (bilancio.py usa la voce del
  padre). I padri che raggruppano voci diverse (per esempio i fondi di
  ammortamento) non hanno voce: i loro sottoconti vanno collegati uno per uno.

Fondi di ammortamento e altre rettifiche
-----------------------------------------
I fondi di ammortamento e il fondo svalutazione crediti sono di tipo ATTIVO e
sono collegati alla stessa voce del bene o del credito che rettificano: il loro
saldo, in Avere, riduce quella voce, che in bilancio compare al netto (art.
2424, il valore netto è quello esposto; il dettaglio dei fondi va in nota
integrativa). Allo stesso modo resi e sconti su vendite e su acquisti, le
rimanenze finali, i prelevamenti del titolare e le imposte anticipate stanno
nel tipo e nella voce del conto che rettificano. RETTIFICHE elenca i conti il cui
saldo normale è opposto a quello della loro voce: bilancio.py non li segnala
come anomali (li segnala, invece, se il saldo è dalla parte della voce).

Saldi di segno opposto
----------------------
Alcuni conti cambiano natura con il segno del saldo: la banca con lo scoperto
è un debito verso banche, l'Erario c/IVA a debito è un debito tributario, il
cliente con saldo Avere ha versato un acconto. VOCI_SALDO_OPPOSTO indica dove
classificarli in quel caso; bilancio.py li sposta e lo segnala, senza
compensarli con gli altri conti della voce (art. 2423-ter, comma 6: divieto di
compenso di partite).

IVA
---
- "IVA su acquisti" (IVA a credito) e "IVA su vendite" (IVA a debito) ricevono
  l'imposta delle singole fatture; alla liquidazione periodica i loro saldi si
  girano a "Erario c/IVA", che a fine periodo è a credito (Dare) o a debito
  (Avere) e si chiude con il versamento.
- IVA indetraibile: quella oggettivamente indetraibile (per esempio sulle spese
  di rappresentanza o la quota indetraibile delle autovetture) è un costo
  accessorio dell'acquisto e si somma al costo del bene o del servizio (OIC 12),
  senza un conto a sé. Quella indetraibile per effetto del pro-rata (art. 19-bis
  D.P.R. 633/1972), che si conosce solo a fine anno e non è attribuibile ai
  singoli acquisti, va nel conto "IVA indetraibile da pro-rata" tra gli oneri
  diversi di gestione (B.14).
- RUOLI dà i conti che il modulo IVA usa per le registrazioni automatiche. I nomi
  dei tre conti IVA sono esattamente quelli che iva.py cerca quando si attiva il
  modulo ("IVA su acquisti", "IVA su vendite", "Erario c/IVA"), così non ne crea
  dei doppioni. iva.py crea l'Erario c/IVA di tipo PASSIVO quando manca; qui è
  ATTIVO tra i crediti tributari: per il bilancio il tipo è indifferente, perché
  conta il segno del saldo (VOCI_SALDO_OPPOSTO).

Limiti
------
- La scadenza oltre i dodici mesi si distingue per conto, non per singola
  partita: per i mutui e i finanziamenti ci sono due sottoconti (quota entro e
  quota oltre l'esercizio successivo), e la quota che scade entro l'anno
  successivo va girata a fine esercizio. Gli altri crediti e debiti sono
  collegati alla voce "entro"; chi ha partite a lunga scadenza deve aprire un
  sottoconto collegato alla voce "oltre".
- I finanziamenti dei soci senza scadenza pattuita sono collegati ai debiti
  esigibili entro l'esercizio successivo (rimborsabili a richiesta); se c'è un
  termine o un vincolo di postergazione oltre i dodici mesi va usato il sottoconto
  "con scadenza oltre l'esercizio successivo".
- Le imposte sul reddito dovute (IRES, IRAP) e i relativi acconti versati hanno
  conti separati: OIC 25 vuole il debito esposto al netto degli acconti e delle
  ritenute, quindi a fine esercizio gli acconti vanno girati a riduzione del
  debito (o, se superiori, il debito a riduzione del credito).
- Il piano non prevede rapporti con imprese del gruppo (controllate, collegate,
  controllanti) né strumenti derivati: le voci esistono negli schemi, i conti
  vanno aggiunti se servono.
- Per la ditta individuale lo schema dell'art. 2424 non è obbligatorio e il
  patrimonio netto è il solo capitale netto del titolare (con i prelevamenti a
  riduzione); IRES e riserve riguardano le società. L'IRPEF del titolare non è
  un costo dell'impresa e non ha conti.
- Il conto "Bilancio di apertura" è la contropartita della riapertura dei conti
  (Database.registra_apertura): dopo la riapertura il suo saldo è il risultato
  degli esercizi precedenti non ancora destinato (attività meno passività
  riportate), per questo è collegato agli utili (perdite) portati a nuovo
  (A.VIII). Dopo la delibera di destinazione dell'utile va girato a riserve,
  utili a nuovo o debiti verso soci per dividendi.
"""

from dataclasses import dataclass

from bilancio_schemi import VOCI_ORDINARIO, FOGLIA


@dataclass(frozen=True)
class ContoBase:
    codice: str
    nome: str
    tipo: str               # ATTIVO, PASSIVO, COSTO, RICAVO
    padre: str = None       # codice del conto padre (None per i conti principali)
    voce: str = None        # foglia dello schema ordinario (bilancio_schemi)
    rettifica: bool = False  # saldo normale opposto a quello della voce
    voce_saldo_opposto: str = None  # dove va il conto se il saldo cambia segno
    nota: str = ""


_CONTI = []


def _padre(codice, nome, tipo, voce=None, rettifica=False, nota=""):
    _CONTI.append(ContoBase(codice, nome, tipo, None, voce, rettifica, nota=nota))
    return codice


def _conto(padre, codice, nome, voce, tipo=None, rettifica=False, saldo_opposto=None, nota=""):
    tipo = tipo or next(c.tipo for c in _CONTI if c.codice == padre)
    _CONTI.append(ContoBase(codice, nome, tipo, padre, voce, rettifica, saldo_opposto, nota))


# --- 1 Immobilizzazioni ---

p = _padre("1100", "Immobilizzazioni immateriali", "ATTIVO")
_conto(p, "1101", "Costi di impianto e di ampliamento", "SPA.B.I.1")
_conto(p, "1102", "Costi di sviluppo", "SPA.B.I.2")
_conto(p, "1103", "Software e diritti di utilizzazione delle opere dell'ingegno", "SPA.B.I.3")
_conto(p, "1104", "Concessioni, licenze e marchi", "SPA.B.I.4")
_conto(p, "1105", "Avviamento", "SPA.B.I.5")
_conto(p, "1106", "Immobilizzazioni immateriali in corso e acconti", "SPA.B.I.6")
_conto(p, "1107", "Altre immobilizzazioni immateriali (migliorie su beni di terzi)", "SPA.B.I.7")

p = _padre("1200", "Fondi ammortamento immobilizzazioni immateriali", "ATTIVO", rettifica=True,
           nota="Rettifiche: saldo Avere che riduce la voce del bene.")
_conto(p, "1201", "F.do amm. costi di impianto e di ampliamento", "SPA.B.I.1", rettifica=True)
_conto(p, "1202", "F.do amm. costi di sviluppo", "SPA.B.I.2", rettifica=True)
_conto(p, "1203", "F.do amm. software e diritti di utilizzazione", "SPA.B.I.3", rettifica=True)
_conto(p, "1204", "F.do amm. concessioni, licenze e marchi", "SPA.B.I.4", rettifica=True)
_conto(p, "1205", "F.do amm. avviamento", "SPA.B.I.5", rettifica=True)
_conto(p, "1207", "F.do amm. altre immobilizzazioni immateriali", "SPA.B.I.7", rettifica=True)

p = _padre("1300", "Immobilizzazioni materiali", "ATTIVO")
_conto(p, "1301", "Terreni", "SPA.B.II.1", nota="Non ammortizzabili.")
_conto(p, "1302", "Fabbricati", "SPA.B.II.1")
_conto(p, "1303", "Impianti e macchinari", "SPA.B.II.2")
_conto(p, "1304", "Attrezzature industriali e commerciali", "SPA.B.II.3")
_conto(p, "1305", "Mobili e arredi", "SPA.B.II.4")
_conto(p, "1306", "Macchine d'ufficio elettroniche", "SPA.B.II.4")
_conto(p, "1307", "Automezzi", "SPA.B.II.4")
_conto(p, "1308", "Altri beni materiali", "SPA.B.II.4")
_conto(p, "1309", "Immobilizzazioni materiali in corso e acconti", "SPA.B.II.5")

p = _padre("1400", "Fondi ammortamento immobilizzazioni materiali", "ATTIVO", rettifica=True,
           nota="Rettifiche: saldo Avere che riduce la voce del bene.")
_conto(p, "1402", "F.do amm. fabbricati", "SPA.B.II.1", rettifica=True)
_conto(p, "1403", "F.do amm. impianti e macchinari", "SPA.B.II.2", rettifica=True)
_conto(p, "1404", "F.do amm. attrezzature industriali e commerciali", "SPA.B.II.3", rettifica=True)
_conto(p, "1405", "F.do amm. mobili e arredi", "SPA.B.II.4", rettifica=True)
_conto(p, "1406", "F.do amm. macchine d'ufficio elettroniche", "SPA.B.II.4", rettifica=True)
_conto(p, "1407", "F.do amm. automezzi", "SPA.B.II.4", rettifica=True)
_conto(p, "1408", "F.do amm. altri beni materiali", "SPA.B.II.4", rettifica=True)

p = _padre("1500", "Immobilizzazioni finanziarie", "ATTIVO")
_conto(p, "1501", "Partecipazioni in altre imprese", "SPA.B.III.1.d-bis")
_conto(p, "1502", "Depositi cauzionali", "SPA.B.III.2.d-bis.oltre",
       nota="Crediti immobilizzati verso altri, di norma esigibili oltre l'esercizio successivo.")
_conto(p, "1503", "Altri titoli immobilizzati", "SPA.B.III.3")

# --- 2 Attivo circolante e ratei attivi ---

p = _padre("2100", "Rimanenze", "ATTIVO")
_conto(p, "2101", "Materie prime, sussidiarie e di consumo", "SPA.C.I.1")
_conto(p, "2102", "Prodotti in corso di lavorazione e semilavorati", "SPA.C.I.2")
_conto(p, "2103", "Lavori in corso su ordinazione", "SPA.C.I.3")
_conto(p, "2104", "Prodotti finiti e merci", "SPA.C.I.4")
_conto(p, "2105", "Acconti a fornitori per acquisti di beni", "SPA.C.I.5")

p = _padre("2200", "Crediti verso clienti", "ATTIVO", "SPA.C.II.1.entro")
_conto(p, "2201", "Clienti", "SPA.C.II.1.entro", saldo_opposto="SPP.D.6.entro",
       nota="Il saldo Avere (cliente che ha pagato in anticipo) è un acconto ricevuto.")
_conto(p, "2202", "Fatture da emettere", "SPA.C.II.1.entro")
_conto(p, "2203", "Effetti e ricevute bancarie in portafoglio", "SPA.C.II.1.entro")
_conto(p, "2204", "Clienti esigibili oltre l'esercizio successivo", "SPA.C.II.1.oltre")
_conto(p, "2209", "Fondo svalutazione crediti", "SPA.C.II.1.entro", rettifica=True,
       nota="Rettifica dei crediti verso clienti: saldo Avere.")

p = _padre("2300", "Crediti tributari", "ATTIVO", "SPA.C.II.5-bis.entro")
_conto(p, "2301", "IVA su acquisti", "SPA.C.II.5-bis.entro", nota="IVA a credito delle fatture passive.")
_conto(p, "2302", "Erario c/IVA", "SPA.C.II.5-bis.entro", saldo_opposto="SPP.D.12.entro",
       nota="Conto di liquidazione: saldo Dare = credito, saldo Avere = debito tributario.")
_conto(p, "2303", "Erario c/acconti IRES", "SPA.C.II.5-bis.entro")
_conto(p, "2304", "Erario c/acconti IRAP", "SPA.C.II.5-bis.entro")
_conto(p, "2305", "Erario c/ritenute subite", "SPA.C.II.5-bis.entro")
_conto(p, "2306", "Crediti d'imposta", "SPA.C.II.5-bis.entro")
_conto(p, "2307", "Crediti per imposte anticipate", "SPA.C.II.5-ter.entro",
       nota="Voce propria C.II.5-ter, non tra i crediti tributari.")

p = _padre("2400", "Altri crediti", "ATTIVO", "SPA.C.II.5-quater.entro")
_conto(p, "2401", "Crediti verso soci per versamenti richiamati", "SPA.A.richiamati")
_conto(p, "2402", "Crediti verso soci per versamenti da richiamare", "SPA.A.non_richiamati")
_conto(p, "2403", "Crediti verso istituti previdenziali", "SPA.C.II.5-quater.entro")
_conto(p, "2404", "Anticipi a fornitori per servizi", "SPA.C.II.5-quater.entro")
_conto(p, "2405", "Crediti verso dipendenti", "SPA.C.II.5-quater.entro")
_conto(p, "2406", "Crediti diversi", "SPA.C.II.5-quater.entro")

p = _padre("2500", "Disponibilità liquide", "ATTIVO")
_conto(p, "2501", "Banca c/c", "SPA.C.IV.1", saldo_opposto="SPP.D.4.entro",
       nota="Con saldo Avere (scoperto) è un debito verso banche.")
_conto(p, "2502", "Conto corrente postale", "SPA.C.IV.1", saldo_opposto="SPP.D.5.entro")
_conto(p, "2503", "Assegni", "SPA.C.IV.2")
_conto(p, "2504", "Cassa contanti", "SPA.C.IV.3")
_conto(p, "2505", "Carte prepagate e valori bollati", "SPA.C.IV.3")

p = _padre("2600", "Ratei e risconti attivi", "ATTIVO", "SPA.D")
_conto(p, "2601", "Ratei attivi", "SPA.D")
_conto(p, "2602", "Risconti attivi", "SPA.D")

# --- 3 Patrimonio netto ---

p = _padre("3100", "Patrimonio netto", "PASSIVO")
_conto(p, "3101", "Capitale sociale (capitale netto per le ditte individuali)", "SPP.A.I")
_conto(p, "3102", "Prelevamenti del titolare (ditte individuali)", "SPP.A.I", rettifica=True,
       nota="Riduce il capitale netto: saldo Dare.")
_conto(p, "3103", "Riserva da soprapprezzo delle quote/azioni", "SPP.A.II")
_conto(p, "3104", "Riserva legale", "SPP.A.IV")
_conto(p, "3105", "Riserve statutarie", "SPP.A.V")
_conto(p, "3106", "Riserva straordinaria", "SPP.A.VI.straordinaria")
_conto(p, "3107", "Versamenti dei soci in conto capitale", "SPP.A.VI.versamenti_capitale")
_conto(p, "3108", "Versamenti dei soci a copertura perdite", "SPP.A.VI.versamenti_copertura_perdite")
_conto(p, "3109", "Utili (perdite) portati a nuovo", "SPP.A.VIII")
_conto(p, "3110", "Utile (perdita) dell'esercizio", "SPP.A.IX",
       nota="Resta a zero durante l'esercizio: in bilancio A.IX riceve il risultato del conto "
            "economico. Riceve il saldo solo con le scritture di chiusura.")
_conto(p, "3199", "Bilancio di apertura", "SPP.A.VIII",
       nota="Contropartita della riapertura dei conti: il saldo è il risultato precedente non destinato.")

# --- 4 Fondi, TFR, debiti e ratei passivi ---

p = _padre("4100", "Fondi per rischi e oneri", "PASSIVO", "SPP.B.4")
_conto(p, "4101", "Fondo trattamento di quiescenza e obblighi simili", "SPP.B.1")
_conto(p, "4102", "Fondo imposte, anche differite", "SPP.B.2")
_conto(p, "4103", "Fondo rischi e oneri futuri", "SPP.B.4")

p = _padre("4200", "Trattamento di fine rapporto", "PASSIVO", "SPP.C")
_conto(p, "4201", "Fondo TFR lavoro subordinato", "SPP.C")

p = _padre("4300", "Debiti finanziari", "PASSIVO")
_conto(p, "4301", "Mutui e finanziamenti bancari - quota entro l'esercizio successivo", "SPP.D.4.entro")
_conto(p, "4302", "Mutui e finanziamenti bancari - quota oltre l'esercizio successivo", "SPP.D.4.oltre")
_conto(p, "4303", "Finanziamenti dei soci", "SPP.D.3.entro",
       nota="Senza scadenza pattuita: rimborsabili a richiesta, quindi entro l'esercizio successivo.")
_conto(p, "4304", "Finanziamenti dei soci con scadenza oltre l'esercizio successivo", "SPP.D.3.oltre")
_conto(p, "4305", "Debiti verso altri finanziatori", "SPP.D.5.entro")

p = _padre("4400", "Debiti verso fornitori", "PASSIVO", "SPP.D.7.entro")
_conto(p, "4401", "Fornitori", "SPP.D.7.entro", saldo_opposto="SPA.C.II.5-quater.entro",
       nota="Il saldo Dare (anticipi o note di credito da incassare) è un credito verso altri.")
_conto(p, "4402", "Fatture da ricevere", "SPP.D.7.entro")
_conto(p, "4403", "Acconti ricevuti da clienti", "SPP.D.6.entro")

p = _padre("4500", "Debiti tributari", "PASSIVO", "SPP.D.12.entro")
_conto(p, "4501", "IVA su vendite", "SPP.D.12.entro", nota="IVA a debito delle fatture attive e dei corrispettivi.")
_conto(p, "4502", "Erario c/ritenute da versare", "SPP.D.12.entro")
_conto(p, "4503", "Erario c/IRES", "SPP.D.12.entro")
_conto(p, "4504", "Erario c/IRAP", "SPP.D.12.entro")
_conto(p, "4505", "Altri debiti tributari", "SPP.D.12.entro")

p = _padre("4600", "Debiti verso istituti di previdenza e di sicurezza sociale", "PASSIVO", "SPP.D.13.entro")
_conto(p, "4601", "INPS c/contributi", "SPP.D.13.entro")
_conto(p, "4602", "INAIL c/premi", "SPP.D.13.entro")
_conto(p, "4603", "Fondi di previdenza complementare", "SPP.D.13.entro")

p = _padre("4700", "Altri debiti", "PASSIVO", "SPP.D.14.entro")
_conto(p, "4701", "Dipendenti c/retribuzioni", "SPP.D.14.entro")
_conto(p, "4702", "Debiti verso amministratori", "SPP.D.14.entro")
_conto(p, "4703", "Soci c/dividendi", "SPP.D.14.entro")
_conto(p, "4704", "Debiti diversi", "SPP.D.14.entro")

p = _padre("4800", "Ratei e risconti passivi", "PASSIVO", "SPP.E")
_conto(p, "4801", "Ratei passivi", "SPP.E")
_conto(p, "4802", "Risconti passivi", "SPP.E")

# --- 5 Valore della produzione e proventi ---

p = _padre("5100", "Ricavi delle vendite e delle prestazioni", "RICAVO", "CE.A.1")
_conto(p, "5101", "Ricavi vendite di merci e prodotti", "CE.A.1")
_conto(p, "5102", "Ricavi per prestazioni di servizi", "CE.A.1")
_conto(p, "5103", "Corrispettivi", "CE.A.1", nota="Vendite al dettaglio, al netto dell'IVA scorporata.")
_conto(p, "5104", "Resi, sconti e abbuoni su vendite", "CE.A.1", rettifica=True,
       nota="Riducono i ricavi (OIC 12): saldo Dare.")

p = _padre("5200", "Variazioni delle rimanenze e incrementi di immobilizzazioni", "RICAVO")
_conto(p, "5201", "Rimanenze iniziali di prodotti in corso, semilavorati e finiti", "CE.A.2",
       nota="Dare: storno delle rimanenze di apertura.")
_conto(p, "5202", "Rimanenze finali di prodotti in corso, semilavorati e finiti", "CE.A.2")
_conto(p, "5203", "Variazione dei lavori in corso su ordinazione", "CE.A.3")
_conto(p, "5204", "Incrementi di immobilizzazioni per lavori interni", "CE.A.4")

p = _padre("5300", "Altri ricavi e proventi", "RICAVO", "CE.A.5.b")
_conto(p, "5301", "Contributi in conto esercizio", "CE.A.5.a")
_conto(p, "5302", "Sopravvenienze attive", "CE.A.5.b",
       nota="Dopo il D.Lgs. 139/2015 non c'è più l'area straordinaria: A.5 se non attribuibili "
            "a una voce per natura.")
_conto(p, "5303", "Plusvalenze da alienazione di beni strumentali", "CE.A.5.b")
_conto(p, "5304", "Rimborsi e recuperi di spese", "CE.A.5.b")
_conto(p, "5305", "Fitti attivi", "CE.A.5.b")
_conto(p, "5306", "Contributi in conto impianti (quota dell'esercizio)", "CE.A.5.b")
_conto(p, "5307", "Altri ricavi e proventi diversi", "CE.A.5.b")
_conto(p, "5308", "Arrotondamenti attivi", "CE.A.5.b")

p = _padre("5400", "Proventi finanziari", "RICAVO", "CE.C.16.d.altri")
_conto(p, "5401", "Interessi attivi bancari e postali", "CE.C.16.d.altri")
_conto(p, "5402", "Interessi attivi su crediti commerciali e di mora", "CE.C.16.d.altri")
_conto(p, "5403", "Dividendi e altri proventi da partecipazioni", "CE.C.15.altri")
_conto(p, "5404", "Utili su cambi", "CE.C.17-bis")

# --- 6 Costi della produzione e oneri finanziari ---

p = _padre("6100", "Costi per materie prime, sussidiarie, di consumo e merci", "COSTO", "CE.B.6")
_conto(p, "6101", "Acquisti di merci", "CE.B.6")
_conto(p, "6102", "Acquisti di materie prime", "CE.B.6")
_conto(p, "6103", "Acquisti di materiali di consumo", "CE.B.6")
_conto(p, "6104", "Carburanti e lubrificanti", "CE.B.6")
_conto(p, "6105", "Cancelleria e stampati", "CE.B.6")
_conto(p, "6106", "Imballaggi", "CE.B.6")
_conto(p, "6107", "Trasporti su acquisti", "CE.B.6", nota="Oneri accessori di acquisto.")
_conto(p, "6108", "Resi, sconti e abbuoni su acquisti", "CE.B.6", rettifica=True,
       nota="Riducono i costi d'acquisto: saldo Avere.")

p = _padre("6200", "Costi per servizi", "COSTO", "CE.B.7")
_conto(p, "6201", "Energia elettrica", "CE.B.7")
_conto(p, "6202", "Gas e riscaldamento", "CE.B.7")
_conto(p, "6203", "Acqua", "CE.B.7")
_conto(p, "6204", "Telefono e internet", "CE.B.7")
_conto(p, "6205", "Consulenze amministrative, fiscali e legali", "CE.B.7")
_conto(p, "6206", "Manutenzioni e riparazioni", "CE.B.7")
_conto(p, "6207", "Trasporti su vendite", "CE.B.7")
_conto(p, "6208", "Pubblicità e promozione", "CE.B.7")
_conto(p, "6209", "Assicurazioni", "CE.B.7")
_conto(p, "6210", "Spese e commissioni bancarie", "CE.B.7",
       nota="Servizi bancari; gli interessi vanno negli oneri finanziari.")
_conto(p, "6211", "Compensi agli amministratori", "CE.B.7")
_conto(p, "6212", "Contributi previdenziali sui compensi agli amministratori", "CE.B.7")
_conto(p, "6213", "Provvigioni passive", "CE.B.7")
_conto(p, "6214", "Lavorazioni di terzi", "CE.B.7")
_conto(p, "6215", "Pulizie", "CE.B.7")
_conto(p, "6216", "Spese postali e di spedizione", "CE.B.7")
_conto(p, "6217", "Viaggi e trasferte", "CE.B.7")
_conto(p, "6218", "Altri servizi", "CE.B.7")

p = _padre("6300", "Costi per godimento di beni di terzi", "COSTO", "CE.B.8")
_conto(p, "6301", "Affitti passivi", "CE.B.8")
_conto(p, "6302", "Canoni di leasing", "CE.B.8", nota="Leasing finanziario con il metodo patrimoniale.")
_conto(p, "6303", "Noleggi", "CE.B.8")
_conto(p, "6304", "Canoni per licenze d'uso e software", "CE.B.8")

p = _padre("6400", "Costi per il personale", "COSTO")
_conto(p, "6401", "Salari e stipendi", "CE.B.9.a")
_conto(p, "6402", "Oneri sociali INPS", "CE.B.9.b")
_conto(p, "6403", "Premi INAIL", "CE.B.9.b")
_conto(p, "6404", "Trattamento di fine rapporto", "CE.B.9.c")
_conto(p, "6405", "Trattamento di quiescenza e simili", "CE.B.9.d")
_conto(p, "6406", "Altri costi del personale", "CE.B.9.e")

p = _padre("6500", "Ammortamenti e svalutazioni", "COSTO")
_conto(p, "6501", "Ammortamento immobilizzazioni immateriali", "CE.B.10.a")
_conto(p, "6502", "Ammortamento immobilizzazioni materiali", "CE.B.10.b")
_conto(p, "6503", "Svalutazioni delle immobilizzazioni", "CE.B.10.c")
_conto(p, "6504", "Svalutazione dei crediti dell'attivo circolante", "CE.B.10.d")

p = _padre("6600", "Variazioni delle rimanenze di materie prime, sussidiarie, di consumo e merci",
           "COSTO", "CE.B.11")
_conto(p, "6601", "Rimanenze iniziali di materie e merci", "CE.B.11",
       nota="Dare: storno delle rimanenze di apertura.")
_conto(p, "6602", "Rimanenze finali di materie e merci", "CE.B.11",
       nota="Avere: rimanenze di chiusura, riducono la voce B.11.")

p = _padre("6700", "Accantonamenti", "COSTO")
_conto(p, "6701", "Accantonamenti per rischi", "CE.B.12")
_conto(p, "6702", "Altri accantonamenti", "CE.B.13")

p = _padre("6800", "Oneri diversi di gestione", "COSTO", "CE.B.14")
_conto(p, "6801", "Imposte e tasse indirette (IMU, registro, bollo, tributi locali)", "CE.B.14")
_conto(p, "6802", "Diritto camerale annuale", "CE.B.14")
_conto(p, "6803", "Tasse di concessione governativa e vidimazioni", "CE.B.14")
_conto(p, "6804", "IVA indetraibile da pro-rata", "CE.B.14",
       nota="Solo l'IVA indetraibile per pro-rata; l'indetraibilità oggettiva va sul costo del bene.")
_conto(p, "6805", "Sopravvenienze passive", "CE.B.14")
_conto(p, "6806", "Minusvalenze da alienazione di beni strumentali", "CE.B.14")
_conto(p, "6807", "Perdite su crediti", "CE.B.14", nota="Per la parte non coperta dal fondo.")
_conto(p, "6808", "Sanzioni e multe", "CE.B.14")
_conto(p, "6809", "Quote associative e abbonamenti", "CE.B.14")
_conto(p, "6810", "Arrotondamenti passivi", "CE.B.14")
_conto(p, "6811", "Altri oneri diversi di gestione", "CE.B.14")

p = _padre("6900", "Interessi e altri oneri finanziari", "COSTO", "CE.C.17.altri")
_conto(p, "6901", "Interessi passivi bancari", "CE.C.17.altri")
_conto(p, "6902", "Interessi passivi su mutui e finanziamenti", "CE.C.17.altri")
_conto(p, "6903", "Interessi passivi di mora e su debiti commerciali", "CE.C.17.altri")
_conto(p, "6904", "Interessi passivi su debiti tributari", "CE.C.17.altri")
_conto(p, "6905", "Altri oneri finanziari", "CE.C.17.altri")
_conto(p, "6906", "Perdite su cambi", "CE.C.17-bis")

# --- 7 Imposte sul reddito ---

p = _padre("7100", "Imposte sul reddito dell'esercizio", "COSTO", "CE.20.correnti")
_conto(p, "7101", "IRES corrente", "CE.20.correnti")
_conto(p, "7102", "IRAP corrente", "CE.20.correnti")
_conto(p, "7103", "Imposte relative a esercizi precedenti", "CE.20.precedenti")
_conto(p, "7104", "Imposte differite", "CE.20.differite_anticipate")
_conto(p, "7105", "Imposte anticipate", "CE.20.differite_anticipate", rettifica=True,
       nota="Riducono le imposte dell'esercizio: saldo Avere.")

del p

CONTI = tuple(_CONTI)
"""Conti nell'ordine del piano: ogni padre seguito dai suoi sottoconti."""

MAPPA = {c.codice: c.voce for c in CONTI if c.voce}
"""Codice del conto -> foglia dello schema ordinario (bilancio_schemi)."""

RETTIFICHE = frozenset(c.codice for c in CONTI if c.rettifica)
"""Conti con il saldo normale opposto a quello della loro voce."""

VOCI_SALDO_OPPOSTO = {c.codice: c.voce_saldo_opposto for c in CONTI if c.voce_saldo_opposto}
"""Codice del conto -> voce in cui classificarlo quando il saldo cambia segno."""

# Conti con un ruolo nelle registrazioni automatiche (modulo IVA, aperture, chiusure)
RUOLI = {
    "iva_acquisti": "2301",          # IVA su acquisti (a credito), Dare nelle fatture passive
    "iva_vendite": "4501",           # IVA su vendite (a debito), Avere nelle fatture attive
    "erario_iva": "2302",            # Erario c/IVA, conto della liquidazione periodica
    "iva_indetraibile_prorata": "6804",
    "clienti": "2201",
    "fornitori": "4401",
    "fatture_da_emettere": "2202",
    "fatture_da_ricevere": "4402",
    "ricavi": "5101",                # ricavo predefinito delle fatture attive
    "ricavi_prestazioni": "5102",
    "corrispettivi": "5103",
    "costi": "6101",                 # costo predefinito delle fatture passive (merci)
    "costi_servizi": "6218",
    "ritenute_da_versare": "4502",
    "cassa": "2504",
    "banca": "2501",
    "apertura": "3199",              # contropartita della riapertura dei conti
    "utile_esercizio": "3110",
    "utili_a_nuovo": "3109",
}


def conti_per_database():
    """Lista (codice, nome, tipo, codice_padre) nell'ordine di inserimento (padri prima dei figli)."""
    return [(c.codice, c.nome, c.tipo, c.padre) for c in CONTI]


def crea_piano(db):
    """
    Inserisce il piano di base in un archivio con il Database di db.py (di norma
    appena creato e senza conti). I conti con un codice già presente sono saltati.
    Restituisce il numero di conti inseriti.
    """
    esistenti = {c["codice"]: c["id"] for c in db.get_conti()}
    inseriti = 0
    for codice, nome, tipo, padre in conti_per_database():
        if codice in esistenti:
            continue
        padre_id = esistenti.get(padre) if padre else None
        esistenti[codice] = db.crea_conto(codice, nome, tipo, padre_id)
        inseriti += 1
    return inseriti


def verifica_piano():
    """Controlli di coerenza del piano (per i test). Restituisce la lista dei problemi."""
    problemi = []
    codici = [c.codice for c in CONTI]
    if len(codici) != len(set(codici)):
        problemi.append("codici duplicati")
    if codici != sorted(codici):
        problemi.append("l'ordine del piano non coincide con l'ordine dei codici")
    padri = {c.codice: c for c in CONTI if c.padre is None}
    for c in CONTI:
        if len(c.codice) != 4 or not c.codice.isdigit():
            problemi.append(f"{c.codice}: il codice deve avere quattro cifre")
        if c.tipo not in ("ATTIVO", "PASSIVO", "COSTO", "RICAVO"):
            problemi.append(f"{c.codice}: tipo {c.tipo} non valido")
        if c.padre is None:
            if not c.codice.endswith("00"):
                problemi.append(f"{c.codice}: un conto padre deve finire con 00")
        else:
            if c.padre not in padri:
                problemi.append(f"{c.codice}: il padre {c.padre} non è un conto principale")
            elif c.codice[:2] != c.padre[:2] or c.codice.endswith("00"):
                problemi.append(f"{c.codice}: codice non coerente con il padre {c.padre}")
            if not c.voce:
                problemi.append(f"{c.codice}: sottoconto senza voce di bilancio")
        for voce in (c.voce, c.voce_saldo_opposto):
            if voce and (voce not in VOCI_ORDINARIO or VOCI_ORDINARIO[voce].genere != FOGLIA):
                problemi.append(f"{c.codice}: la voce {voce} non è una foglia dello schema ordinario")
        if c.voce:
            patrimoniale = c.tipo in ("ATTIVO", "PASSIVO")
            if patrimoniale != c.voce.startswith("SP"):
                problemi.append(f"{c.codice}: tipo {c.tipo} collegato alla voce {c.voce}")
    for ruolo, codice in RUOLI.items():
        if codice not in codici:
            problemi.append(f"ruolo {ruolo}: conto {codice} inesistente")
    return problemi
