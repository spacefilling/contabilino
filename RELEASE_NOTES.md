## Contabilino — Contabilità in partita doppia per piccole attività

Programma autonomo per Windows: registra costi e ricavi in partita doppia, gestisce gli esercizi contabili, mostra i saldi dei conti ed esporta in CSV, Excel e PDF. **Non richiede installazione né Python**: un solo file da avviare.

### 🆕 Novità di questa versione
- **Molto più veloce**: nella 1.5 ogni clic rallentava per colpa del tema grafico. Lo stile Windows 11 ora è disegnato direttamente e l'interfaccia risponde subito, come prima.
- **Nuova scheda Partitari**: scegli un conto e vedi tutti i suoi movimenti con il saldo progressivo (per un conto padre anche quelli dei sottoconti). Doppio clic su un movimento per aprirlo nel Libro Giornale; pulsante Esporta per CSV, Excel e PDF.
- **Conti e sottoconti ad albero**: nel piano dei conti, nei Saldi Conti (con il totale di ogni gruppo, da aprire e chiudere) e nella scelta dei conti da esportare. Doppio clic su un conto nei Saldi per aprire il suo partitario.
- L'export dei Saldi Conti riporta i totali di gruppo, come la scheda.
- **Icona**: il logo nella barra del titolo e nella barra delle applicazioni viene ora dal file `.ico` con il metodo nativo di Windows, anche nelle finestre di avvio.
- **Proprietà del file**: `Contabilino.exe` riporta descrizione, versione e copyright di spacefiller (Proprietà → Dettagli).
- Nessuna modifica al database: gli archivi esistenti si usano così come sono.

**Se vedi ancora l'icona vecchia**: togli Contabilino dalla barra delle applicazioni e aggiungilo di nuovo; per l'icona del file in Esplora risorse esegui `ie4uinit.exe -show` dal Prompt dei comandi (o rinomina il file).

### ⬇️ Download
Scarica **`Contabilino.exe`** dalla sezione *Assets* qui sotto. Firma del codice: [Code signing policy](https://spacefilling.github.io/contabilino/firma-del-codice/).
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
- Report Costi e Ricavi e Partitari di qualsiasi conto (fornitori, clienti, banca…), anche da consultare in una scheda.
- Piano dei conti e saldi ad albero, con i totali di gruppo.
- Export CSV (compatibile Excel italiano), Excel `.xlsx` e PDF.
