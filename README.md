# Contabilino – contabilità in partita doppia per piccole attività

[![Versione](https://img.shields.io/github/v/release/spacefilling/contabilino?label=versione)](https://github.com/spacefilling/contabilino/releases/latest)
[![Licenza: GPL v3](https://img.shields.io/badge/licenza-GPLv3-blue.svg)](LICENSE)
![Windows](https://img.shields.io/badge/Windows-.exe%20portabile-0078d4)
![macOS](https://img.shields.io/badge/macOS-app-555555)
![Linux](https://img.shields.io/badge/Linux-eseguibile-f5b800)
![Python](https://img.shields.io/badge/Python-Tkinter%20%2B%20SQLite-3776ab)

**Registra costi e ricavi in partita doppia senza un gestionale.** Contabilino è un programma gratuito e open source (GPL-3.0) per Windows, Mac e Linux, pensato per piccole attività, associazioni e professionisti che tengono una contabilità essenziale: libro giornale, piano dei conti con clienti e fornitori, esercizi contabili con riporto dei saldi, costi e ricavi, partitari, export in CSV, Excel e PDF.

> **Niente installazione, tutto in una cartella.**
> - **Non si installa**: è un unico file, `Contabilino.exe`. Lo copi in una cartella (anche su una chiavetta USB) e lo avvii con un doppio clic. Non serve Python, non serve essere amministratori.
> - **I dati stanno in un solo file**: l'archivio `contabilino.db`, accanto al programma.
> - **Si sposta e si salva copiando**: per il backup copia il file `.db`; per passare a un altro computer copia la cartella (programma + archivio) e riparti da lì.
> - **Non lascia tracce**: non scrive nel registro di Windows né in altre cartelle. Per toglierlo basta cancellare la cartella.

**Sito e manuale:** [spacefilling.github.io/contabilino](https://spacefilling.github.io/contabilino/) · [Manuale](https://spacefilling.github.io/contabilino/manuale/)

**Download (ultima versione):** [Windows](https://github.com/spacefilling/contabilino/releases/latest/download/Contabilino.exe) · [Mac Apple Silicon](https://github.com/spacefilling/contabilino/releases/latest/download/Contabilino-mac-apple-silicon.zip) · [Mac Intel](https://github.com/spacefilling/contabilino/releases/latest/download/Contabilino-mac-intel.zip) · [Linux](https://github.com/spacefilling/contabilino/releases/latest/download/Contabilino-linux.tar.gz) · [Code signing policy](https://spacefilling.github.io/contabilino/firma-del-codice/)

![Contabilino su Windows 11: libro giornale con la riga di inserimento rapido](docs/assets/schermate/01-libro-giornale.png)

## Funzioni

- **Libro giornale con inserimento rapido**: una riga per registrazione (data, causale, conto Dare, conto Avere, importo), tutto da tastiera. La data si scrive compatta (`20260315` → `15/03/2026`), conti e causali si completano mentre scrivi, l'importo si digita come su un registratore di cassa.
- **Correzione, eliminazione e storno** delle registrazioni, con la scelta se rinumerare le successive. Le registrazioni di un esercizio chiuso sono protette.
- **Piano dei conti con sottoconti**: per esempio `400 Costi generali` con un sottoconto per ogni fornitore e `500 Ricavi generali` con un sottoconto per ogni cliente.
- **Esercizi contabili con periodo libero**, anche a cavallo tra due anni (es. 01/07/2026 – 30/06/2027), da aprire e chiudere.
- **Riporto dei saldi**: creando un nuovo esercizio, il programma propone di riportare i saldi di cassa, banca, crediti e debiti, con la differenza (utile compreso) su un conto di patrimonio netto.
- **Numerazione in ordine di data**: se registri un'operazione con una data precedente all'ultima, il programma chiede se rinumerare il giornale.
- **Saldi conti ad albero**: ogni conto padre con il totale del gruppo e i sottoconti da aprire e chiudere, con verifica della quadratura Dare/Avere.
- **Costi e ricavi**: solo i conti di costo e di ricavo, con il totale di ogni gruppo e il risultato dell'esercizio (utile o perdita).
- **Partitari**: una scheda per consultare i movimenti di un conto (clienti, fornitori, banca, costi, ricavi…) con data, numero, causale, contropartita, Dare, Avere e saldo progressivo, e l'export di tutti i partitari.
- **Scelta dei conti da esportare**: tutti, oppure quelli spuntati in un elenco, anche per intervallo di codici (es. da 401 a 449) o cercandoli per nome.
- **Registrazioni composte** con più conti (stipendi, ammortamenti, fatture con IVA).
- **Export in CSV, Excel e PDF** di tutti i report. Il PDF è pronto da stampare o da mandare al commercialista.

**Moduli facoltativi** (Strumenti → Moduli; spenti, il programma funziona come prima):
- **Gestione IVA**: fatture e note di credito di acquisto e vendita, corrispettivi, reverse charge, IVA indetraibile; registri IVA sezionali configurabili, stampabili per mese, trimestre o anno; liquidazione mensile o trimestrale con giroconto su Erario c/IVA.
- **Bilancio civilistico**: stato patrimoniale e conto economico negli schemi del Codice civile (ordinario artt. 2424-2425, abbreviato art. 2435-bis, micro-imprese art. 2435-ter), con confronto con l'esercizio precedente e controlli. I conti si collegano alle voci, anche solo in parte; per gli archivi nuovi c'è un piano dei conti completo già collegato.

## Download e avvio

Nessuna installazione: si scarica un file e si avvia.


1. Scarica [`Contabilino.exe`](https://github.com/spacefilling/contabilino/releases/latest/download/Contabilino.exe) dall'[ultima release](https://github.com/spacefilling/contabilino/releases/latest).
2. Mettilo in una cartella (anche su una chiavetta USB) e fai doppio clic.
3. Al primo avvio Windows può mostrare l'avviso *"Windows ha protetto il PC"*: l'eseguibile non è firmato digitalmente. Clicca **Ulteriori informazioni → Esegui comunque**.
4. Nella finestra di benvenuto scegli **Crea un nuovo archivio**: il file `contabilino.db` nasce nella stessa cartella e ai successivi avvii si apre da solo. Se nella cartella c'è già un archivio di Contabilino (anche con un altro nome), la finestra lo propone.

### Mac

Scarica lo zip per il tuo Mac ([Apple Silicon](https://github.com/spacefilling/contabilino/releases/latest/download/Contabilino-mac-apple-silicon.zip): M1 e successivi; [Intel](https://github.com/spacefilling/contabilino/releases/latest/download/Contabilino-mac-intel.zip)), aprilo e **trascina `Contabilino.app` nella cartella dove vuoi tenere i dati** (anche una chiavetta). L'app non è firmata da Apple: la prima volta macOS la blocca. Clic destro sull'app → **Apri** → **Apri**, oppure Impostazioni di Sistema → Privacy e sicurezza → **Apri comunque**. L'archivio `contabilino.db` sta accanto a `Contabilino.app`.

### Linux

Scarica [`Contabilino-linux.tar.gz`](https://github.com/spacefilling/contabilino/releases/latest/download/Contabilino-linux.tar.gz), estrailo in una cartella e avvia `./Contabilino` (doppio clic o dal terminale). Funziona sulle distribuzioni con glibc 2.35 o successiva (es. Ubuntu 22.04 e seguenti, Debian 12, Fedora 36). L'archivio sta accanto all'eseguibile.

Per provarlo con dati inventati, copia [`esempi/contabilino-esempio.db`](esempi/) accanto all'eseguibile e avvia il programma: la finestra di benvenuto lo propone.

## Report ed export

Menu **Export**: ogni report ha i tre formati.

| Report | Cosa contiene |
| --- | --- |
| Libro Giornale | tutte le registrazioni dell'esercizio |
| Saldi Conti | totale Dare, totale Avere e saldo di ogni conto |
| Costi e Ricavi | conti di costo e ricavo con totali di gruppo e risultato dell'esercizio |
| Partitari | i movimenti di ogni conto scelto, con saldo progressivo (proposti: i conti di costo e ricavo) |

- **CSV**: separatore punto e virgola e codifica UTF-8 con BOM, si apre direttamente in Excel italiano.
- **Excel** (`.xlsx`): titolo ed esercizio in alto, importi in formato numerico, totali, impostato per la stampa.
- **PDF**: A4 con intestazioni ripetute su ogni pagina e numero di pagina.

Esempi di export generati dal database di prova: [`esempi/`](esempi/).

## Documentazione

- [Presentazione](https://spacefilling.github.io/contabilino/)
- [Manuale completo](https://spacefilling.github.io/contabilino/manuale/)
- Le stesse informazioni in testo semplice: [`GUIDA RAPIDA.txt`](GUIDA%20RAPIDA.txt) e [`GUIDA ESTESA.txt`](GUIDA%20ESTESA.txt), allegate anche a ogni release.

## Dati e backup

| Cosa | Dove |
| --- | --- |
| Registrazioni, conti, esercizi | il file `.db` (SQLite) accanto al programma |
| Backup | basta copiare il file `.db` |
| Aggiornamento del formato | fatto in automatico all'apertura, con una copia di sicurezza del `.db` prima della conversione |

Il database è un normale file SQLite: si può aprire anche con altri strumenti (es. [DB Browser for SQLite](https://sqlitebrowser.org/)).

## Eseguire dal codice sorgente

Serve Python 3.10 o successivo (Tkinter è incluso in Python per Windows e macOS).

```bash
pip install -r requirements.txt
python main.py
```

Dipendenze: `openpyxl` (export Excel), `reportlab` (export PDF), `pyinstaller` (solo per creare l'eseguibile).

### Creare l'eseguibile

```bash
python strumenti/versione_exe.py
pyinstaller --onefile --windowed --name Contabilino --icon risorse/contabilino.ico --hidden-import openpyxl --version-file versione_exe.txt --add-data "risorse/contabilino.ico;risorse" main.py
```

Su Windows c'è anche [`build.bat`](build.bat). Ogni tag `vX.Y` pubblicato su GitHub avvia la [build automatica](.github/workflows/build.yml) dell'`.exe` e lo allega alla release.

| File | Contenuto |
| --- | --- |
| `main.py` | avvio, scelta o creazione del database |
| `tema.py` | aspetto in stile Windows 11, font, zoom dello schermo, icona |
| `ui.py` | finestra principale: libro giornale, saldi, menu |
| `dialogs.py` | esercizi, piano dei conti, eliminazione e storno, scelta dei conti da esportare |
| `widgets.py` | campi data, importo e autocompletamento |
| `db.py` | database SQLite e aggiornamento automatico del formato |
| `export.py` | report e scrittura in CSV, Excel e PDF (anche registri IVA, liquidazione, bilancio) |
| `iva.py`, `iva_ui.py` | modulo IVA: registri, documenti, liquidazione |
| `bilancio_schemi.py`, `bilancio.py`, `bilancio_ui.py` | modulo bilancio: schemi del Codice civile, calcolo, finestre |
| `piano_base.py` | piano dei conti completo collegato alle voci di bilancio |
| `dateutils.py` | date e periodi degli esercizi |
| `icona.py` | logo e caselle di spunta incorporati (generato da `strumenti/genera_icone.py`) |
| `strumenti/` | generazione di logo, icone e informazioni di versione dell'eseguibile, screenshot e tempi di risposta su Windows |
| `.signpath/` | configurazione per la firma del codice con SignPath |

## Note e limiti

- Il modulo IVA non gestisce pro-rata generale, IVA per cassa, ventilazione dei corrispettivi, regimi speciali, split payment e plafond; il bilancio non produce nota integrativa, rendiconto finanziario né il file XBRL per il deposito.
- **Non sostituisce il commercialista** e non fa dichiarazioni, F24 o comunicazioni: i dati vanno controllati da chi firma.
- Gli eseguibili sono per Windows a 64 bit, Mac (Apple Silicon e Intel) e Linux a 64 bit. Su Mac l'app non è firmata da Apple, su Windows l'eseguibile non è ancora firmato (vedi [Code signing policy](https://spacefilling.github.io/contabilino/firma-del-codice/)).
- Non sostituisce il commercialista: serve a tenere in ordine i movimenti e a passargli dati chiari.

## Contribuire

Segnalazioni di errori e proposte sono benvenute nelle [issue](https://github.com/spacefilling/contabilino/issues), così come le pull request.

## Firma del codice

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/). La firma è in fase di attivazione: dettagli, ruoli e privacy nella [Code signing policy](https://spacefilling.github.io/contabilino/firma-del-codice/).

## Licenza

Contabilino è software libero, rilasciato con la [GNU General Public License v3.0](LICENSE) (GPL-3.0-or-later).

Puoi usarlo per qualsiasi scopo, anche per lavoro, e puoi studiarlo, modificarlo e condividerlo. Se distribuisci Contabilino o una sua versione modificata, devi farlo con la stessa licenza e insieme al codice sorgente. Non può diventare un prodotto chiuso e proprietario. Il programma è fornito così com'è, senza alcuna garanzia.

Copyright (C) 2026 spacefiller.
