---
title: 'Firma del codice (Code signing policy)'
description: 'Come vengono firmate le release di Contabilino per Windows: firma gratuita di SignPath Foundation, ruoli del progetto e privacy.'
permalink: /firma-del-codice/
---

# Firma del codice

<p class="lead">Code signing policy di Contabilino: come e da chi vengono firmati gli eseguibili per Windows.</p>

## Firma con SignPath Foundation

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

Contabilino è un progetto open source e per firmare l'eseguibile Windows usa il programma gratuito di SignPath Foundation per i progetti open source. Il certificato è intestato a SignPath Foundation, che quindi compare come editore del file firmato.

**Stato:** la firma è in fase di attivazione. Finché non è attiva, le release di Contabilino non sono firmate e Windows mostra l'avviso *"Windows ha protetto il PC"* al primo avvio (vedi [Avvio]({{ '/manuale/#avvio' | relative_url }})).

### Cosa viene firmato

- Solo `Contabilino.exe`, compilato dal codice sorgente di questo repository: [{{ site.repository_url }}]({{ site.repository_url }}).
- L'eseguibile viene compilato in modo automatico da GitHub Actions, su macchine di GitHub, a partire dal tag della versione ([workflow di build]({{ site.repository_url }}/blob/main/.github/workflows/build.yml)). Nessun file viene compilato o firmato a mano.
- Ogni richiesta di firma viene approvata a mano da un approvatore del progetto prima che la firma venga applicata.
- Le librerie incluse nell'eseguibile (Python, Tk, openpyxl, reportlab, PyInstaller) sono software open source dei rispettivi autori.

## Ruoli del progetto

| Ruolo | Chi |
| --- | --- |
| Autori (committer) | [spacefiller](https://github.com/spacefilling), proprietario del repository |
| Revisori | [spacefiller](https://github.com/spacefilling): i contributi esterni (pull request) vengono rivisti prima di essere accettati |
| Approvatori delle firme | [spacefiller](https://github.com/spacefilling) |

Tutti i membri con accesso al repository o alla firma usano l'autenticazione a più fattori, sia su GitHub sia su SignPath.

## Privacy

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

Contabilino non trasmette informazioni ad altri sistemi in rete, salvo quando è l'utente a chiederlo: l'unico caso è il comando **? → Manuale online**, che apre questo sito nel browser. Tutti i dati contabili restano nel file `.db` sul computer o sulla chiavetta dell'utente.

## Installazione e rimozione

Contabilino non ha un programma di installazione e non modifica il sistema: è un unico file `.exe`. Per rimuoverlo basta cancellare `Contabilino.exe` (e, se non servono più, i file `.db` con i dati).

## Segnalazioni

Per segnalare un problema di sicurezza o un uso improprio della firma, apri una [issue]({{ site.repository_url }}/issues) sul repository.
