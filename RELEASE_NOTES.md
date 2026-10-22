## Contabilino — Contabilità in partita doppia per piccole attività

Programma per **Windows, Mac e Linux**: registra costi e ricavi in partita doppia, gestisce gli esercizi contabili, mostra saldi e partitari ed esporta in CSV, Excel e PDF.

> **Non si installa.** Un solo file da avviare; i dati stanno in un solo file (`contabilino.db`) accanto al programma. Per il backup o per passare a un altro computer basta copiare la cartella.

### 🆕 Novità di questa versione
- **Anche per Mac e Linux**: app per Mac (Apple Silicon e Intel) ed eseguibile per Linux, portabili come quello per Windows.
- **Finestra di benvenuto** più chiara: spiega dove stanno i dati e, se nella cartella del programma trova un archivio di Contabilino (anche con un altro nome), lo propone con numero di registrazioni e data di modifica. Poi: crea un nuovo archivio, apri un archivio da un'altra cartella, esci. Se c'è `contabilino.db` si apre subito, come prima.
- **File → Apri archivio** controlla che il file sia davvero un archivio di Contabilino; nuovo comando **File → Mostra la cartella dell'archivio** (comodo per il backup).
- Documentazione e sito mettono in evidenza che il programma è portabile.
- Nessuna modifica al database: gli archivi esistenti si usano così come sono.

### ⬇️ Download
Dalla sezione *Assets* qui sotto scarica il file per il tuo sistema:
- **Windows**: `Contabilino.exe`
- **Mac**: `Contabilino-mac-apple-silicon.zip` (M1 e successivi) oppure `Contabilino-mac-intel.zip`
- **Linux**: `Contabilino-linux.tar.gz` (glibc 2.35 o successiva: Ubuntu 22.04 e seguenti, Debian 12, Fedora 36…)

Firma del codice: [Code signing policy](https://spacefilling.github.io/contabilino/firma-del-codice/). Facoltativo: `GUIDA RAPIDA.txt` e `GUIDA ESTESA.txt` sono le guide in italiano.

### ▶️ Come si usa
**Windows** — copia `Contabilino.exe` in una cartella (anche su chiavetta) e fai doppio clic. La prima volta Windows può mostrare *"Windows ha protetto il PC"*: l'eseguibile non è ancora firmato. Clicca **Ulteriori informazioni → Esegui comunque** (oppure, prima di avviarlo: tasto destro → Proprietà → *Annulla blocco*).

**Mac** — apri lo zip e trascina `Contabilino.app` nella cartella dove vuoi tenere i dati. L'app non è firmata da Apple: la prima volta fai **clic destro → Apri → Apri** (oppure Impostazioni di Sistema → Privacy e sicurezza → *Apri comunque*).

**Linux** — estrai l'archivio nella cartella dove vuoi tenere i dati e avvia `./Contabilino`.

Al primo avvio scegli **Crea un nuovo archivio**: nasce `contabilino.db` accanto al programma e dalle volte successive si apre da solo.

### 💾 Dati e backup
- Tutti i dati stanno nel file **`contabilino.db`** accanto al programma (su Mac accanto a `Contabilino.app`).
- Per il backup basta **copiare quel file** altrove. Fallo periodicamente.
- Struttura tipica su chiavetta:
  ```
  CHIAVETTA
  ├── Contabilino.exe   (o Contabilino.app, o Contabilino)
  └── contabilino.db
  ```

### 📌 Note
- Gli eseguibili sono generati automaticamente da GitHub Actions a partire dal codice di questo tag.

### ✨ Funzioni principali
- Per Windows, Mac (Apple Silicon e Intel) e Linux, senza installazione.
- Libro giornale con inserimento rapido (data compatta, autocompletamento conti/causali, importo stile registratore di cassa).
- Correzione, eliminazione (con scelta sulla numerazione) e storno delle registrazioni.
- Piano dei conti con conti e sottoconti.
- Gestione esercizi con periodo libero, anche a cavallo tra due anni (apri/chiudi/modifica).
- Saldi conti con verifica di quadratura Dare/Avere.
- Riporto dei saldi tra esercizi e numerazione in ordine di data.
- Report Costi e Ricavi e Partitari di qualsiasi conto (fornitori, clienti, banca…), anche da consultare in una scheda.
- Piano dei conti e saldi ad albero, con i totali di gruppo.
- Export CSV (compatibile Excel italiano), Excel `.xlsx` e PDF.
