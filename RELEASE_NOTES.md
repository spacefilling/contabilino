## Contabilino — Contabilità in partita doppia per piccole attività

Programma autonomo per Windows: registra costi e ricavi in partita doppia, gestisce gli esercizi contabili, mostra i saldi dei conti ed esporta in CSV, Excel e PDF. **Non richiede installazione né Python**: un solo file da avviare.

### 🆕 Novità di questa versione
**Report ed export**
- **Export in PDF** di tutti i report, pronto da stampare o inviare (A4, intestazioni ripetute su ogni pagina, numero di pagina).
- **Nuovo report Costi e Ricavi**: solo i conti di costo e di ricavo, con il totale per gruppo (es. 400 con i suoi sottoconti) e il risultato dell'esercizio (utile o perdita).
- **Nuovi Partitari**: per ogni conto (fornitori, clienti, banca, costi, ricavi…) i movimenti con data, numero, causale, contropartita, Dare, Avere e saldo progressivo. È proposta la scelta "solo i conti di costo e ricavo".
- **Scelta dei conti da esportare** (Saldi Conti, Costi e Ricavi, Partitari): tutti, oppure solo quelli spuntati, uno alla volta, per intervallo di codici (es. da 401 a 449) o cercandoli per nome. Spuntando un conto padre si spuntano anche i suoi sottoconti.
- Menu **Export** con una voce per report e i tre formati CSV, Excel, PDF. L'Excel ha titolo ed esercizio in alto ed è impostato per la stampa.

**Esercizi e numerazione**
- **Riporto dei saldi**: creando un nuovo esercizio il programma chiede se riportare i saldi di cassa, banca, crediti e debiti dall'esercizio precedente, con la differenza su un conto di patrimonio netto. C'è anche il pulsante **Riporta saldi…** in Gestione Esercizi.
- **Numerazione in ordine di data**: se registri un'operazione con una data precedente all'ultima, il programma chiede se rinumerare il giornale. Comando anche in **Esercizio → Rinumera in ordine di data**.
- Chiusura e riapertura di un esercizio chiedono conferma; il periodo di un esercizio chiuso non si può più cambiare.

**Correzioni**
- Un nuovo sottoconto eredita davvero il tipo del conto padre (prima veniva proposto COSTO). Avviso se si sceglie un tipo diverso dal padre, o se si cambia il tipo di un conto che ha già movimenti.
- Non si possono più creare sottoconti di sottoconti, che sparivano dai totali.
- Campo importo: Incolla e Taglia aggiornano davvero l'importo (prima il campo poteva mostrare un valore e salvarne un altro).
- Una registrazione non può più restare salvata a metà se il database dà errore (es. chiavetta scollegata).
- Date compatte: `25122026` ora è il 25/12/2026 (prima le date dal 19 al 31 in formato GGMMAAAA venivano rifiutate); `1/2/26` vale 2026.
- Niente più "-0,00" in tabelle ed export; formato degli importi in Excel corretto.
- Nei nuovi database il conto 300 Crediti clienti è di tipo ATTIVO (prima PASSIVO). Nei database esistenti si può correggere da Conti → Gestione Piano dei Conti.
- Nessuna modifica alla struttura del database: gli archivi esistenti si usano così come sono.

### ⬇️ Download
Scarica **`Contabilino.exe`** dalla sezione *Assets* qui sotto.
(Facoltativo: `GUIDA RAPIDA.txt` e `GUIDA ESTESA.txt` sono le guide in italiano.)

### ▶️ Come si usa
1. Copia `Contabilino.exe` dove vuoi (anche su una chiavetta USB) e fai **doppio clic**.
2. **Primo avvio** — Windows può mostrare l'avviso blu *"Windows ha protetto il PC"*: è normale (l'eseguibile non è firmato, non è un virus). Clicca **"Ulteriori informazioni" → "Esegui comunque"**. Capita solo la prima volta.
3. Al primo avvio scegli **crea un nuovo database** (oppure aprine uno esistente). I dati finiscono in un unico file `contabilino.db` nella stessa cartella del programma.

### 💾 Dati e backup
- Tutti i dati stanno nel file **`contabilino.db`** accanto all'eseguibile.
- Per il backup basta **copiare quel file** altrove. Fallo periodicamente.
- Struttura tipica su chiavetta:
  ```
  CHIAVETTA
  ├── Contabilino.exe
  └── contabilino.db
  ```

### 📌 Note
- Sistema operativo: **Windows** (64 bit).
- L'eseguibile è generato automaticamente da GitHub Actions a partire dal codice di questo tag.

### ✨ Funzioni principali
- Libro giornale con inserimento rapido (data compatta, autocompletamento conti/causali, importo stile registratore di cassa).
- Correzione, eliminazione (con scelta sulla numerazione) e storno delle registrazioni.
- Piano dei conti con conti e sottoconti.
- Gestione esercizi con periodo libero, anche a cavallo tra due anni (apri/chiudi/modifica).
- Saldi conti con verifica di quadratura Dare/Avere.
- Riporto dei saldi tra esercizi e numerazione in ordine di data.
- Report Costi e Ricavi e Partitari di qualsiasi conto (fornitori, clienti, banca…).
- Export CSV (compatibile Excel italiano), Excel `.xlsx` e PDF.
