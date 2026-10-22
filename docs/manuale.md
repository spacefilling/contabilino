---
title: 'Manuale di Contabilino'
description: 'Manuale di Contabilino: avvio, esercizi e riporto dei saldi, piano dei conti con clienti e fornitori, libro giornale, correzioni, storni e numerazione, saldi, costi e ricavi, partitari, export in CSV, Excel e PDF, backup.'
permalink: /manuale/
---

# Manuale di Contabilino

<nav class="toc" aria-label="Indice">
<strong>Indice</strong>
<ol>
  <li><a href="#avvio">Avvio</a></li>
  <li><a href="#primo-utilizzo">Primo utilizzo</a></li>
  <li><a href="#esercizi">Esercizi</a></li>
  <li><a href="#piano-dei-conti">Piano dei conti</a></li>
  <li><a href="#registrare-unoperazione">Registrare un'operazione</a></li>
  <li><a href="#correggere-eliminare-o-stornare">Correggere, eliminare o stornare</a></li>
  <li><a href="#saldi-conti">Saldi conti</a></li>
  <li><a href="#report-ed-export">Report ed export</a></li>
  <li><a href="#scorciatoie-da-tastiera">Scorciatoie da tastiera</a></li>
  <li><a href="#dati-backup-e-chiavetta-usb">Dati, backup e chiavetta USB</a></li>
  <li><a href="#limiti-da-conoscere">Limiti da conoscere</a></li>
  <li><a href="#eseguire-dal-codice-sorgente">Eseguire dal codice sorgente</a></li>
</ol>
</nav>

## 1. Avvio {#avvio}

Scarica [`Contabilino.exe`]({{ site.download_url }}) dall'[ultima release]({{ site.repository_url }}/releases/latest) e mettilo in una cartella, anche su una chiavetta USB. Non c'è niente da installare.

Al primo avvio Windows può mostrare l'avviso *"Windows ha protetto il PC"*: l'eseguibile non è firmato digitalmente. Clicca **Ulteriori informazioni → Esegui comunque**. Capita solo la prima volta.

All'avvio il programma cerca il file `contabilino.db` nella sua cartella:

- se c'è, lo apre;
- se non c'è, chiede se **creare un nuovo database** o **aprirne uno esistente**.

Altri database si aprono o si creano da **File → Apri Database** e **File → Nuovo Database**.

Quando una nuova versione cambia il formato del database, il programma lo aggiorna da solo all'apertura e prima salva una copia di sicurezza del file, avvisando dove si trova.

## 2. Primo utilizzo {#primo-utilizzo}

1. Crea un nuovo database.
2. Crea un esercizio da **Esercizio → Gestione Esercizi** (vedi [Esercizi](#esercizi)).
3. Se serve, completa il piano dei conti da **Conti → Gestione Piano dei Conti**: ci sono già sei conti predefiniti. Aggiungi un sottoconto per ogni cliente e fornitore.
4. Registra le operazioni nella scheda **Libro Giornale**.

Per provare il programma con dati inventati, usa il database di esempio [`esempi/contabilino-esempio.db`]({{ site.repository_url }}/tree/main/esempi): copialo accanto all'eseguibile e rinominalo `contabilino.db`, oppure aprilo da **File → Apri Database**.

## 3. Esercizi {#esercizi}

Menu **Esercizio → Gestione Esercizi**.

| Comando | Cosa fa |
| --- | --- |
| Nuovo | crea un esercizio indicandone il periodo |
| Modifica | cambia descrizione e date |
| Chiudi / Riapri | chiude o riapre l'esercizio |
| Elimina | cancella l'esercizio, solo se non ha registrazioni |
| Riporta saldi… | registra all'inizio dell'esercizio i saldi di apertura presi dall'esercizio precedente |
| Seleziona | rende attivo l'esercizio (anche con doppio clic) |

L'esercizio ha una **data di inizio** e una **data di fine**, quindi non deve per forza coincidere con l'anno solare: `01/01/2026 – 31/12/2026`, ma anche `01/07/2026 – 30/06/2027`.

Nella finestra del nuovo esercizio la data di fine viene proposta a dodici mesi meno un giorno dalla data di inizio, e i pulsanti **Anno solare** e **1 luglio – 30 giugno** compilano le date con un clic. Anche la descrizione è proposta in automatico (es. *Esercizio 2026/2027*) e si può cambiare.

Regole:

- la data di fine deve essere successiva alla data di inizio;
- due esercizi non possono sovrapporsi;
- ogni registrazione deve avere una data compresa nel periodo dell'esercizio attivo.

L'esercizio attivo è indicato in alto a destra nella finestra. Registrazioni, saldi ed export si riferiscono sempre all'esercizio attivo. All'avvio il programma seleziona l'esercizio aperto che contiene la data di oggi.

In un **esercizio chiuso** non si possono aggiungere, modificare o eliminare registrazioni (si possono solo stornare in un esercizio aperto) e non se ne può cambiare il periodo. Chiusura e riapertura chiedono conferma.

### Riporto dei saldi {#riporto-dei-saldi}

Ogni esercizio conta solo i propri movimenti: senza riporto, Cassa, Banca, crediti e debiti del nuovo esercizio partirebbero da zero. Quando crei un esercizio e il precedente ha dei saldi di attivo e passivo, il programma chiede se **riportarli**; si può fare anche più tardi con **Riporta saldi…**.

La finestra del riporto mostra i saldi che verranno registrati e chiede il **conto di patrimonio netto** da usare come contropartita: uno esistente di tipo PASSIVO oppure uno nuovo (proposto: *290 – Patrimonio netto*). Per ogni conto di attivo e passivo con saldo diverso da zero viene creata una registrazione *Saldo di apertura* al primo giorno dell'esercizio:

- conto di attivo (es. Banca 5.350,00 in Dare): Dare Banca, Avere Patrimonio netto;
- conto di passivo (es. Debiti fornitori 1.200,00 in Avere): Dare Patrimonio netto, Avere Debiti fornitori.

![Finestra del riporto dei saldi con anteprima delle registrazioni]({{ '/assets/schermate/05-riporto-saldi.png' | relative_url }}){: .esempio width="460"}

Alla fine il patrimonio netto ha come saldo la differenza tra attività e passività, cioè il capitale più gli utili (o meno le perdite) accumulati. I conti di costo e ricavo non si riportano: ogni esercizio ha i suoi.

Conviene riportare i saldi quando l'esercizio precedente è completo, meglio se già chiuso: se dopo il riporto cambi le registrazioni dell'esercizio precedente, i saldi di apertura non si aggiornano da soli. Se l'esercizio contiene già delle aperture, la finestra lo segnala, perché riportando di nuovo i saldi verrebbero contati due volte.

## 4. Piano dei conti {#piano-dei-conti}

Menu **Conti → Gestione Piano dei Conti**. Conti predefiniti di un nuovo database:

| Codice | Conto | Tipo |
| --- | --- | --- |
| 100 | Cassa | ATTIVO |
| 110 | Banca | ATTIVO |
| 200 | Debiti fornitori | PASSIVO |
| 300 | Crediti clienti | ATTIVO |
| 400 | Costi generali | COSTO |
| 500 | Ricavi generali | RICAVO |

I tipi sono **ATTIVO**, **PASSIVO**, **COSTO** e **RICAVO**. Il report Costi e Ricavi e i Partitari usano i conti di tipo COSTO e RICAVO.

### Sottoconti per clienti e fornitori

Seleziona un conto e premi **Nuovo sottoconto**. Il sottoconto eredita il tipo del conto padre. Un modo pratico di organizzarsi è un sottoconto per ogni fornitore sotto i costi e uno per ogni cliente sotto i ricavi:

```
400 - Costi generali
    401 - Molino Valle Verde S.r.l.
    402 - Energia Nord S.p.A.
    403 - Affitto laboratorio
500 - Ricavi generali
    501 - Trattoria Il Portico
    502 - Bottega Gastronomica Sole
```

Il report Costi e Ricavi mostra così il totale di ogni fornitore e cliente, e i Partitari le loro fatture.

I pagamenti e gli incassi però passano da Banca, Cassa, 200 Debiti fornitori e 300 Crediti clienti. Se ti serve sapere quanto resta da pagare o da incassare a ciascuno, crea un sottoconto per fornitore anche sotto 200 (e per cliente sotto 300) e registra lì fatture e pagamenti: il partitario di quel sottoconto mostra il debito o il credito ancora aperto.

I livelli sono due, conto e sottoconto: un sottoconto non può avere a sua volta sottoconti.

Lasciando dei numeri liberi tra un gruppo e l'altro (es. 401–449 materie prime, 450–499 servizi) diventa facile esportare un gruppo intero con l'[intervallo di codici](#scelta-dei-conti).

Un conto non si può eliminare se ha movimenti o sottoconti.

## 5. Registrare un'operazione {#registrare-unoperazione}

![Libro giornale con la riga di inserimento]({{ '/assets/schermate/01-libro-giornale.png' | relative_url }}){: .esempio}

La riga di inserimento è in fondo alla scheda **Libro Giornale**: **Data**, **Causale**, **Conto Dare**, **Conto Avere**, **Importo**. Si compila tutta da tastiera, con <kbd>Tab</kbd> per passare al campo successivo.

1. **Data**: scrivila compatta, `20260212` o `12022026`, e al <kbd>Tab</kbd> diventa `12/02/2026`. Va bene anche `12/02/2026` o `1/7/2026`.
2. **Causale**: mentre scrivi compaiono le causali già usate. Scegli con le frecce e <kbd>Invio</kbd>, oppure scrivi un testo nuovo.
3. **Conto Dare**: scrivi parte del codice o del nome (es. `cas` per Cassa, `40` per i costi) e scegli dall'elenco.
4. **Conto Avere**: come sopra.
5. **Importo**: si digita come su un registratore di cassa, solo cifre, la virgola si mette da sola: `10000` → `100,00`, `1500` → `15,00`, `50` → `0,50`.
6. <kbd>Invio</kbd> sull'importo (o **Salva**) registra. La riga si svuota e il cursore torna sulla data.

Esempi:

| Operazione | Dare | Avere |
| --- | --- | --- |
| Fattura di un fornitore (senza IVA, o con IVA non detraibile) | 401 Molino Valle Verde | 200 Debiti fornitori |
| Pagamento in contanti di una spesa | 400 Costi generali | 100 Cassa |
| Fattura a un cliente | 300 Crediti clienti | 501 Trattoria Il Portico |
| Incasso su banca | 110 Banca | 300 Crediti clienti |

Una fattura con IVA detraibile richiede due registrazioni: l'imponibile sul conto di costo e l'IVA su un conto *IVA a credito*, entrambe in Avere su 200 Debiti fornitori.

## 6. Correggere, eliminare o stornare {#correggere-eliminare-o-stornare}

Seleziona la registrazione nella tabella: sotto si attivano i pulsanti **Modifica**, **Elimina** e **Storno**, presenti anche nel menu del tasto destro.

### Modifica

Doppio clic sulla riga, oppure <kbd>Invio</kbd>. La registrazione torna nella riga di inserimento, che diventa *Modifica registrazione n. …*: correggi e salva, il numero resta lo stesso. <kbd>Esc</kbd> o **Annulla** rinunciano alla modifica.

### Elimina

Tasto <kbd>Canc</kbd> o pulsante **Elimina**. La conferma mostra tutti i dati della registrazione e chiede cosa fare della numerazione:

- **Lascia i numeri come sono**: il numero eliminato resta libero (11, 13, 14…);
- **Rinumera**: le registrazioni successive scalano di un numero e non restano buchi. Cambiano però i numeri di registrazioni che potresti aver già stampato o esportato.

L'eliminazione è definitiva.

### Numerazione in ordine di data {#numerazione}

Il libro giornale va numerato in ordine di data. Il numero di una nuova registrazione è il successivo all'ultimo: se registri un'operazione con una data precedente a registrazioni già inserite (es. una fattura arrivata in ritardo), dopo il salvataggio il programma lo segnala e chiede se **rinumerare le registrazioni dell'esercizio in ordine di data**. Lo stesso comando è nel menu **Esercizio → Rinumera in ordine di data…**, solo per gli esercizi aperti.

Rinumerando cambiano i numeri di registrazioni che potresti aver già stampato o esportato, e i numeri citati nelle causali (es. *Storno reg. n. …*) restano quelli vecchi: conviene rinumerare prima di stampare il giornale definitivo.

### Storno

Invece di cancellare, aggiunge una nuova registrazione con gli stessi conti invertiti e lo stesso importo: l'effetto sui saldi si annulla e nel giornale restano sia l'originale sia lo storno. La causale proposta è *Storno reg. n. … del …*.

Lo storno va nell'esercizio che contiene la data scelta, che deve essere aperto. Così si può correggere anche una registrazione di un esercizio già chiuso.

## 7. Saldi conti {#saldi-conti}

La scheda **Saldi Conti** mostra per ogni conto il totale Dare, il totale Avere e il saldo (Dare − Avere), con i sottoconti rientrati sotto il conto padre. Il saldo ha sempre lo stesso verso: per i conti di passivo e di ricavo un saldo normale è negativo (vedi [Limiti](#limiti-da-conoscere)).

![Scheda Saldi Conti]({{ '/assets/schermate/03-saldi-conti.png' | relative_url }}){: .esempio} In fondo ci sono i totali generali: il totale Dare deve essere uguale al totale Avere.

## 8. Report ed export {#report-ed-export}

Menu **Export**: ogni report ha un sottomenu con i tre formati, **CSV**, **Excel** e **PDF**. Gli export riguardano sempre l'esercizio attivo.

| Report | Contenuto |
| --- | --- |
| Libro Giornale | tutte le registrazioni: numero, data, causale, conto Dare, conto Avere, importo |
| Saldi Conti | totale Dare, totale Avere e saldo di ogni conto |
| Costi e Ricavi | i conti di costo e ricavo con movimenti, totali di gruppo e risultato dell'esercizio |
| Partitari | per ogni conto scelto, i movimenti con saldo progressivo |

### Costi e Ricavi

Mostra i conti di tipo COSTO e RICAVO che hanno movimenti nell'esercizio, con gli importi in positivo (i costi in Dare, i ricavi in Avere). Un conto con sottoconti riporta in grassetto il totale del gruppo e sotto il dettaglio dei sottoconti; i movimenti registrati direttamente sul conto padre hanno una riga a parte. In fondo: totale ricavi, totale costi e **utile** o **perdita**.

![Report Costi e Ricavi in PDF]({{ '/assets/esempio-costi-e-ricavi.png' | relative_url }}){: .esempio}

### Partitari

Per ogni conto scelto (un fornitore, un cliente, la banca, un conto di costo…): data, numero e causale della registrazione, **contropartita** (l'altro conto della registrazione), Dare, Avere e **saldo progressivo**. Il saldo segue il verso naturale del conto, così cresce con i movimenti normali: Dare − Avere per i conti di attivo e di costo, Avere − Dare per i conti di passivo e di ricavo. Compaiono solo i conti con movimenti nell'esercizio.

Nella scelta dei conti la prima opzione, proposta, è **Solo i conti di costo e ricavo**.

![Partitari in PDF]({{ '/assets/esempio-partitari.png' | relative_url }}){: .esempio}

### Scelta dei conti {#scelta-dei-conti}

Per **Saldi Conti**, **Costi e Ricavi** e **Partitari**, prima di salvare si sceglie quali conti esportare:

- solo per i Partitari, **Solo i conti di costo e ricavo**;
- **Tutti i conti**, oppure
- **Solo i conti spuntati nell'elenco**. Per spuntarli:
  - clic sul conto (o <kbd>barra spaziatrice</kbd>): spunta o toglie la spunta. Spuntando un conto padre si spuntano anche i suoi sottoconti, per esempio 400 con tutti i fornitori registrati sotto 400;
  - **Codici da … a …** e **Spunta intervallo**: spunta tutti i conti con il codice in quell'intervallo, per esempio da 401 a 449;
  - **Cerca**: mostra solo i conti che contengono il testo nel codice o nel nome, e **Spunta tutti quelli in elenco** spunta quelli trovati.

![Scelta dei conti da esportare]({{ '/assets/schermate/04-scelta-conti.png' | relative_url }}){: .esempio width="420"}

I metodi si combinano: per esempio un intervallo di fornitori più due clienti cercati per nome. Per Costi e Ricavi l'elenco comprende solo i conti di costo e ricavo, per Saldi Conti e Partitari tutti i conti.

Il PDF e l'Excel riportano in alto i conti scelti. Con una selezione, Costi e Ricavi calcola il risultato solo sui conti selezionati. Il programma ricorda l'ultima scelta finché resta aperto.

### Formati

| Formato | Caratteristiche |
| --- | --- |
| CSV | separatore punto e virgola e codifica UTF-8 con BOM: si apre direttamente in Excel italiano. Nel CSV dei partitari ogni riga riporta codice e nome del conto, così si può filtrare. |
| Excel | titolo ed esercizio in alto, intestazioni in grassetto, importi in formato numerico, righe di totale, impostato per stampare su una pagina di larghezza. |
| PDF | A4 (orizzontale per il Libro Giornale), intestazioni ripetute su ogni pagina, numero di pagina in fondo. |

Se il file da sovrascrivere è aperto in Excel o in un lettore PDF, il programma non riesce a salvarlo: chiudilo e ripeti l'export.

## 9. Scorciatoie da tastiera {#scorciatoie-da-tastiera}

| Tasto | Dove | Azione |
| --- | --- | --- |
| <kbd>Tab</kbd> | riga di inserimento | campo successivo, conferma la voce suggerita |
| <kbd>Invio</kbd> | riga di inserimento | conferma la voce dell'elenco, sull'importo salva |
| <kbd>Invio</kbd> o doppio clic | tabella | modifica la registrazione selezionata |
| <kbd>Esc</kbd> | riga di inserimento | svuota la riga o annulla la modifica |
| <kbd>Canc</kbd> | tabella | elimina la registrazione selezionata |
| Tasto destro | tabella | menu con Modifica, Elimina, Storno |
| <kbd>↑</kbd> <kbd>↓</kbd> | autocompletamento | scorre l'elenco dei suggerimenti |

## 10. Dati, backup e chiavetta USB {#dati-backup-e-chiavetta-usb}

Tutti i dati stanno in un solo file `.db` (SQLite). Per il **backup** basta copiarlo in un altro posto: fallo con regolarità. Il file si apre anche con altri strumenti, per esempio [DB Browser for SQLite](https://sqlitebrowser.org/).

Per usare Contabilino da una **chiavetta USB** copia sulla chiavetta l'eseguibile e il database:

```
E:\
├── Contabilino.exe
└── contabilino.db
```

All'avvio il programma apre da solo il `contabilino.db` che si trova nella sua cartella.

## 11. Limiti da conoscere {#limiti-da-conoscere}

Contabilino tiene una contabilità in partita doppia essenziale. Alcune cose non le fa, e conviene saperlo:

- **Riporto dei saldi, non chiusura dei conti.** Il [riporto](#riporto-dei-saldi) registra i saldi di apertura nel nuovo esercizio, ma il programma non fa le scritture di chiusura dell'esercizio precedente né la destinazione dell'utile: il risultato confluisce nel patrimonio netto.
- **Il segno dei saldi.** Nella scheda Saldi Conti e nel suo export il saldo è sempre Dare − Avere: per i conti di passivo e di ricavo un saldo "normale" è quindi negativo. Il report Costi e Ricavi invece mostra costi e ricavi entrambi in positivo.
- **Fornitori e clienti come costi e ricavi.** Se sono sottoconti di 400 e 500, il loro partitario elenca le fatture ma non i pagamenti: per lo scadenzario servono i sottoconti sotto 200 e 300 (vedi [Piano dei conti](#piano-dei-conti)).
- **IVA.** Ogni registrazione ha un conto in Dare e uno in Avere: una fattura con IVA detraibile si registra in due righe, l'imponibile sul conto di costo e l'IVA su un conto "IVA a credito" (da creare, di tipo ATTIVO). Registrando il totale sul costo, i costi risultano più alti. Contabilino non tiene i registri IVA.
- **Non è un software fiscale.** Non produce registri obbligatori, dichiarazioni o bilancio civilistico e non sostituisce il commercialista: serve a tenere in ordine i movimenti e a passargli dati chiari.

## 12. Eseguire dal codice sorgente {#eseguire-dal-codice-sorgente}

Serve Python 3.10 o successivo. Tkinter è incluso in Python per Windows e macOS.

```bash
git clone {{ site.repository_url }}.git
cd contabilino
pip install -r requirements.txt
python main.py
```

Per creare l'eseguibile Windows:

```bash
python strumenti/versione_exe.py
pyinstaller --onefile --windowed --name Contabilino --icon risorse/contabilino.ico --hidden-import openpyxl --collect-data sv_ttk --version-file versione_exe.txt main.py
```

L'eseguibile si trova in `dist\Contabilino.exe`. Su Windows lo stesso si ottiene con `build.bat`. Le release su GitHub vengono compilate in automatico a ogni nuova versione.

Segnalazioni e proposte: [issue su GitHub]({{ site.repository_url }}/issues).
