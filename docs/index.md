---
title: 'Contabilità in partita doppia per piccole attività, gratis per Windows'
description: 'Contabilino è un programma gratuito e open source per Windows: libro giornale in partita doppia, clienti e fornitori, riporto dei saldi, costi e ricavi, partitari, export in CSV, Excel e PDF. Un solo file .exe, senza installazione.'
permalink: /
faq:
  - q: 'Contabilino è gratuito?'
    a: 'Sì. Contabilino è gratuito e open source, con licenza GNU GPL v3. Puoi usarlo anche per la tua attività; le versioni modificate si possono distribuire solo con la stessa licenza e con il codice sorgente.'
  - q: 'Serve installarlo?'
    a: 'No. È un unico file `Contabilino.exe`: lo copi in una cartella, anche su una chiavetta USB, e lo avvii con un doppio clic. Non serve nemmeno installare Python.'
  - q: 'Dove sono salvati i dati?'
    a: 'In un solo file `contabilino.db` (un database SQLite) nella stessa cartella del programma. Per il backup basta copiare quel file.'
  - q: 'Come tengo i conti dei singoli clienti e fornitori?'
    a: 'Crea un sottoconto per ciascuno: per esempio sotto `400 Costi generali` un sottoconto per ogni fornitore, sotto `500 Ricavi generali` uno per ogni cliente. Il report Costi e Ricavi mostra il totale di ognuno, i Partitari l''elenco dei loro movimenti.'
  - q: 'Posso esportare solo alcuni clienti o fornitori?'
    a: 'Sì. Per Saldi Conti, Costi e Ricavi e Partitari scegli tutti i conti oppure solo quelli spuntati in un elenco: uno per uno, per intervallo di codici (es. da 401 a 449) o cercandoli per nome.'
  - q: 'Gestisce l''IVA e il bilancio?'
    a: 'No. Contabilino tiene una contabilità in partita doppia essenziale: registrazioni con un conto in Dare e uno in Avere, saldi, costi e ricavi, partitari. Una fattura con IVA si registra in due righe (imponibile e IVA), ma il programma non tiene i registri IVA e non fa il bilancio civilistico. Non è un software fiscale e non corrisponde al regime di "contabilità semplificata".'
  - q: 'Funziona su Mac o Linux?'
    a: 'L''eseguibile pronto è per Windows. Dal codice sorgente, con Python, Contabilino funziona anche su macOS e Linux.'
---

# Contabilino

<p class="lead">Contabilità in partita doppia per piccole attività, su Windows. Registri costi e ricavi da tastiera, tieni i conti di clienti e fornitori e ottieni report pronti da stampare o da mandare al commercialista.</p>

{% include download.html %}

![Contabilino su Windows 11: libro giornale con la riga di inserimento rapido]({{ '/assets/schermate/01-libro-giornale.png' | relative_url }})

## Che cos'è Contabilino?

Contabilino è un piccolo programma per chi deve tenere una contabilità in **partita doppia** senza un gestionale: piccole attività, associazioni, professionisti. Ogni operazione è una riga del libro giornale con un conto in Dare, un conto in Avere e un importo. Da quelle righe il programma ricava saldi, costi e ricavi, partitari di clienti e fornitori.

È un solo file `.exe` che non richiede installazione, e i dati stanno in un solo file `.db` accanto al programma: si può tenere tutto su una chiavetta USB.

## Funzioni

- **Libro giornale con inserimento rapido**: data compatta (`20260315` diventa `15/03/2026`), conti e causali che si completano mentre scrivi, importo come su un registratore di cassa. <kbd>Tab</kbd> per passare al campo successivo, <kbd>Invio</kbd> per salvare.
- **Correzione, eliminazione e storno** delle registrazioni, con la scelta se rinumerare le successive.
- **Piano dei conti con sottoconti**: un sottoconto per ogni cliente e fornitore.
- **Esercizi contabili** con periodo libero, anche a cavallo tra due anni, e **riporto dei saldi** di apertura nel nuovo esercizio.
- **Numerazione in ordine di data**, con la proposta di rinumerare quando registri un'operazione arretrata.
- **Saldi conti** con verifica della quadratura Dare/Avere.
- **Costi e ricavi** con totali per gruppo e risultato dell'esercizio.
- **Partitari** di qualsiasi conto (clienti, fornitori, banca, costi, ricavi) con saldo progressivo.
- **Export in CSV, Excel e PDF**, per tutti i conti o solo per quelli scelti.

## Schermate

<figure class="figura">
  <img class="esempio" src="{{ '/assets/schermate/03-saldi-conti.png' | relative_url }}" alt="Scheda Saldi Conti con totale Dare, totale Avere e saldo di ogni conto">
  <figcaption>Saldi Conti: totali e saldo di ogni conto, con la verifica della quadratura.</figcaption>
</figure>

<figure class="figura">
  <img class="esempio" src="{{ '/assets/schermate/04-scelta-conti.png' | relative_url }}" alt="Scelta dei conti da esportare con caselle di spunta e intervallo di codici" width="420">
  <figcaption>Scelta dei conti da esportare: tutti, solo costi e ricavi, o quelli spuntati.</figcaption>
</figure>

## Report

<figure class="figura">
  <img class="esempio" src="{{ '/assets/esempio-costi-e-ricavi.png' | relative_url }}" alt="Report Costi e Ricavi in PDF: costi e ricavi per conto, totali e utile dell'esercizio">
  <figcaption>Costi e Ricavi: ogni fornitore e cliente con il suo totale e, in fondo, l'utile o la perdita dell'esercizio.</figcaption>
</figure>

<figure class="figura">
  <img class="esempio" src="{{ '/assets/esempio-partitari.png' | relative_url }}" alt="Partitari dei fornitori in PDF: movimenti con data, causale, contropartita e saldo progressivo">
  <figcaption>Partitari: i movimenti di ogni conto con data, causale, contropartita e saldo progressivo.</figcaption>
</figure>

Gli stessi report, insieme a Libro Giornale e Saldi Conti, si salvano in CSV ed Excel. Tutti gli esempi, generati da un database di prova con dati inventati, sono nella cartella [`esempi`]({{ site.repository_url }}/tree/main/esempi) del progetto.

## Come si comincia

1. Scarica [`Contabilino.exe`]({{ site.download_url }}) e mettilo in una cartella.
2. Avvialo con un doppio clic. Al primo avvio Windows può mostrare l'avviso *"Windows ha protetto il PC"*, perché il programma non è firmato digitalmente: clicca **Ulteriori informazioni → Esegui comunque**.
3. Crea un nuovo database, poi un esercizio (**Esercizio → Gestione Esercizi**).
4. Aggiungi i sottoconti di clienti e fornitori (**Conti → Gestione Piano dei Conti**) e inizia a registrare.

Tutti i passaggi sono spiegati nel [manuale]({{ '/manuale/' | relative_url }}).

{% include faq.html %}
