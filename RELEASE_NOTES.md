## Contabilino — Contabilità in partita doppia per piccole attività

Programma per **Windows, Mac e Linux**: registra costi e ricavi in partita doppia, gestisce gli esercizi contabili, mostra saldi e partitari ed esporta in CSV, Excel e PDF.

> **Non si installa.** Un solo file da avviare; i dati stanno in un solo file (`contabilino.db`) accanto al programma. Per il backup o per passare a un altro computer basta copiare la cartella.

### 🆕 Novità di questa versione
**Due moduli facoltativi**, da attivare per l'archivio in *Strumenti → Moduli*. Spenti, Contabilino funziona esattamente come prima: chi lo usa già non deve cambiare nulla.

- **Gestione IVA**: fatture e note di credito di acquisto e vendita, corrispettivi (con scorporo), reverse charge, IVA indetraibile. La scrittura contabile la prepara il programma. Registri IVA sezionali configurabili, stampabili per mese, trimestre o anno; liquidazione mensile o trimestrale con interessi dell'1%, credito riportato, acconto e giroconto su Erario c/IVA.
- **Bilancio civilistico**: stato patrimoniale e conto economico negli schemi del Codice civile (ordinario, abbreviato, micro-imprese), con confronto con l'esercizio precedente, controlli e stampa. I conti si collegano alle voci di bilancio, anche solo in parte, con proposte automatiche.

E inoltre:
- **Piano dei conti completo** (circa 200 conti già collegati al bilancio) proposto quando crei un archivio nuovo; il piano semplice resta la scelta predefinita.
- **Registrazione composta**: operazioni con più di due conti (stipendi, ammortamenti...).
- Nessun dato esistente viene modificato: solo aggiunte, vuote finché non usi i moduli.

> Contabilino aiuta a tenere in ordine contabilità, IVA e bilancio, ma non sostituisce il commercialista: non fa dichiarazioni, F24, nota integrativa né il deposito XBRL.

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
