# Changelog

## 2.0 – 2026-10-22

- **Gestione IVA** (modulo facoltativo): registri sezionali configurabili (vendite, acquisti, corrispettivi), fatture e note di credito, corrispettivi con scorporo, reverse charge con integrazione nel registro vendite, IVA indetraibile per riga; protocollo per registro e anno; stampa dei registri per mese, trimestre o anno con riepilogo per aliquota; liquidazione mensile o trimestrale con interessi dell'1%, credito riportato, minimo di 25,82 euro, acconto e giroconto su Erario c/IVA.
- **Bilancio civilistico** (modulo facoltativo): schemi ordinario (artt. 2424-2425 c.c.), abbreviato (art. 2435-bis) e micro-imprese (art. 2435-ter), confronto con l'esercizio precedente, unità di euro, controlli (quadratura, conti non collegati, saldi opposti, scritture di chiusura); collegamento facoltativo dei conti alle voci con proposte automatiche.
- **Piano dei conti completo** (circa 200 conti collegati al bilancio) proposto alla creazione di un archivio nuovo; il piano semplice resta la scelta predefinita.
- **Registrazioni composte** con più di due conti, gestite in giornale, partitari, saldi ed export (libro giornale in formato classico quando servono).
- Strumenti → Moduli per attivare o spegnere IVA e bilancio; con i moduli spenti il programma funziona come prima.
- Nessun dato esistente viene modificato: solo tabelle e colonne nuove, vuote finché non si usano.

## 1.7 – 2026-10-22

- Versioni per Mac (Apple Silicon e Intel, `.app`) e Linux, oltre a Windows; build e release automatiche per tutti e tre.
- Finestra di benvenuto: propone gli archivi di Contabilino trovati nella cartella, crea o apre un archivio; `contabilino.db` si apre subito come prima.
- File → Apri archivio verifica che il file sia un archivio di Contabilino; File → Mostra la cartella dell'archivio.
- Su Mac l'archivio sta accanto a `Contabilino.app`; messaggio chiaro se macOS avvia l'app da una posizione temporanea.
- Documentazione: portabilità in evidenza (non si installa, dati in un solo file, si sposta copiando la cartella).
- Firma del codice con SignPath Foundation in preparazione: pagina [Code signing policy](https://spacefilling.github.io/contabilino/firma-del-codice/) e firma automatica nel workflow di build, attiva quando il progetto viene approvato.

## 1.6 – 2026-10-22

- **Interfaccia molto più veloce**: il tema Sun Valley della 1.5 rallentava ogni clic (circa 70 ms per selezionare una riga); lo stile Windows 11 ora è disegnato direttamente, con tempi di risposta 7-8 volte più bassi.
- **Nuova scheda Partitari**: si sceglie un conto e se ne vedono i movimenti con saldo progressivo; per un conto padre, anche quelli dei sottoconti. Doppio clic su un movimento per aprirlo nel Libro Giornale; export del partitario in CSV, Excel e PDF.
- **Saldi Conti ad albero**: i sottoconti stanno dentro il conto padre, che riporta il totale del gruppo; gruppi da aprire e chiudere. Doppio clic su un conto per aprirne il partitario. Anche l'export dei saldi riporta i totali di gruppo.
- **Piano dei conti ad albero**: codice e nome rientrati sotto il conto padre, numero di sottoconti, doppio clic per modificare.
- Scelta dei conti da esportare ad albero.
- Icona della finestra e della barra delle applicazioni dal file `.ico` (metodo nativo di Windows), anche nelle finestre di avvio.
- Eseguibile con informazioni di versione: descrizione, versione e copyright di spacefiller in Proprietà → Dettagli.

## 1.5 – 2026-10-22

- Aspetto in stile Windows 11 (tema Sun Valley, font Segoe UI, pulsanti principali in evidenza) e intestazione con logo ed esercizio attivo.
- Testo nitido con lo zoom di Windows (125%, 150%…); la finestra si adatta allo schermo.
- Logo come icona della finestra, della barra delle applicazioni e del file `.exe`.
- La tendina dei conti si chiude passando a un altro campo, con un clic in un altro punto della finestra o passando a un altro programma (prima restava aperta fino a "Pulisci").
- Scelta dei conti con caselle di spunta in stile Windows 11.
- Database di esempio con incassi, pagamenti e versamenti in banca.

## 1.4 – 2026-10-22

Prima versione pubblica.

Report ed export
- Export in PDF di tutti i report (A4, intestazioni ripetute su ogni pagina, numero di pagina).
- Nuovo report **Costi e Ricavi**: conti di costo e ricavo con totali di gruppo e risultato dell'esercizio (utile o perdita).
- Nuovi **Partitari** di qualsiasi conto, con data, numero, causale, contropartita, Dare, Avere e saldo progressivo nel verso naturale del conto.
- Scelta dei conti da esportare per Saldi Conti, Costi e Ricavi e Partitari: tutti, solo costi e ricavi (partitari), oppure quelli spuntati, anche per intervallo di codici o con la ricerca per nome. PDF ed Excel riportano in alto la selezione.
- Menu Export con una voce per report e i tre formati CSV, Excel e PDF.
- Excel: titolo ed esercizio in alto, formato numerico degli importi corretto, impostazioni di stampa.

Esercizi e numerazione
- Riporto dei saldi di attivo e passivo nel nuovo esercizio, con contropartita un conto di patrimonio netto; proposto alla creazione dell'esercizio.
- Rinumerazione del giornale in ordine di data, proposta quando si registra un'operazione con data precedente all'ultima.
- Conferma per chiusura e riapertura; periodo di un esercizio chiuso non modificabile.

Correzioni (da una revisione contabile del codice)
- Il nuovo sottoconto eredita il tipo del padre; avvisi per tipo diverso dal padre e per cambio di tipo di un conto con movimenti.
- Bloccati i sottoconti di sottoconti (i loro movimenti sparivano dai totali).
- Campo importo: Incolla e Taglia aggiornano l'importo salvato.
- Registrazione salvata in un'unica transazione: niente registrazioni a metà in caso di errore del database.
- Date compatte GGMMAAAA accettate per tutti i giorni del mese; anni a due cifre letti come 20xx; anni prima del 1900 rifiutati.
- Niente "-0,00" dagli arrotondamenti.
- Aggiornamento dei database della versione 1.0/1.1: l'esercizio inizia il 1° gennaio dell'anno, non alla data di apertura.
- Sottoconto di tipo diverso dal padre mostrato senza rientro in Costi e Ricavi.
- Nei nuovi database 300 Crediti clienti è di tipo ATTIVO.
- Menu **?** con il link al manuale online e le informazioni su versione e licenza.
- Nessuna modifica alla struttura del database.

## 1.3 – 2026-09-11

- Modifica delle registrazioni: doppio clic, Invio o pulsante Modifica; il numero resta lo stesso.
- Eliminazione con conferma dei dati completi e scelta se rinumerare le registrazioni successive.
- Storno: nuova registrazione con Dare e Avere invertiti, anche per registrazioni di esercizi chiusi.
- Registrazioni degli esercizi chiusi protette da modifica ed eliminazione.
- Autocompletamento: Tab conferma la voce identica al testo scritto.
- Saldi Conti: contano solo i movimenti dell'esercizio selezionato.

## 1.2 – 2026-08-06

- Esercizio contabile con periodo libero (data di inizio e di fine), anche a cavallo tra due anni.
- Aggiornamento automatico dei database esistenti, con copia di sicurezza del file prima della conversione.
- Controllo dei periodi sovrapposti, modifica ed eliminazione degli esercizi.
- La data di una registrazione deve cadere nel periodo dell'esercizio.

## 1.1 – 2026-06-29

- Release con titolo e note di rilascio automatici.

## 1.0 – 2026-06-29

- Libro giornale con inserimento rapido, piano dei conti con sottoconti, esercizi, saldi conti.
- Export CSV ed Excel.
- Eseguibile Windows portabile generato automaticamente con GitHub Actions.
