## Contabilino — Contabilità in partita doppia per piccole attività

Programma autonomo per Windows: registra costi e ricavi in partita doppia, gestisce gli esercizi contabili, mostra i saldi dei conti ed esporta in CSV, Excel e PDF. **Non richiede installazione né Python**: un solo file da avviare.

### 🆕 Novità di questa versione
- **Nuovo aspetto in stile Windows 11**: tema chiaro e pulito, font Segoe UI, pulsanti principali in evidenza, intestazione con il logo e l'esercizio attivo (con il pulsante **Esercizi…** per cambiarlo).
- **Testo nitido sugli schermi con zoom** (125%, 150%…): prima Windows ingrandiva la finestra sfocandola. La finestra si adatta sempre allo schermo.
- **Logo di Contabilino** come icona della finestra, della barra delle applicazioni e del file `Contabilino.exe`.
- **Tendina dei conti corretta**: si chiude passando a un altro campo, con un clic in un altro punto della finestra o passando a un altro programma (prima restava aperta fino a "Pulisci").
- Scelta dei conti da esportare con caselle di spunta in stile Windows 11.
- Database di esempio più realistico, con incassi, pagamenti e versamenti in banca.
- Nessuna modifica al database: gli archivi esistenti si usano così come sono.

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
