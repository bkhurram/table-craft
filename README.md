<p align="center">
  <img src="assets/icons/elephant-craft.png" alt="Icona TableCraft: elefante inciso su fondo corallo" width="144">
</p>

<h1 align="center">TableCraft</h1>

<p align="center">
  <b>Uno spazio di lavoro per SQL, tabelle e connessioni su macOS.</b><br>
  Personalizzazione locale di TablePlus con identità Craft, profilo separato e strumenti di analisi riproducibili.
</p>

<p align="center">
  <img alt="Piattaforma: macOS" src="https://img.shields.io/badge/platform-macOS-333333">
  <img alt="Architettura verificata: Apple Silicon" src="https://img.shields.io/badge/verified-Apple%20Silicon-F45B32">
  <img alt="Stato sperimentale" src="https://img.shields.io/badge/status-experimental-E5A200">
  <img alt="Licenza del codice del repository: MIT" src="https://img.shields.io/badge/repository%20code-MIT-168B65">
</p>

<p align="center">
  <a href="#funzionalità">Funzionalità</a> ·
  <a href="#compatibilità">Compatibilità</a> ·
  <a href="#installazione">Installazione</a> ·
  <a href="docs/architecture.md">Architettura</a> ·
  <a href="README.en.md">English</a>
</p>

<p align="center">
  <img src="docs/images/sqlite-filters.png" alt="Database SQLite sintetico con tre filtri applicati e due righe risultanti" width="100%">
  <br><sub>Una tabella SQLite di prova, filtri combinati e risultati nello stesso workspace.</sub>
</p>

## Il progetto

TableCraft raccoglie gli script per creare e personalizzare una copia locale di
TablePlus: icona, schermata iniziale, nome dell'app, menu e profilo dei dati.
Il motore database e l'interfaccia nativa provengono dall'app installata separatamente.

Questo repository contiene il codice degli strumenti e gli asset originali del
progetto. Il sorgente di TablePlus, i suoi binari e i profili utente non sono
inclusi. Non è disponibile una build autonoma da compilare dal solo repository.

## Funzionalità

- **Identità Craft:** elefante inciso nero/avorio su fondo corallo, icona macOS e logo interno coordinati.
- **Interfaccia personalizzata:** nome TableCraft nella schermata iniziale, nei menu e nella finestra Informazioni.
- **Profilo separato:** connessioni e impostazioni locali in `analysis/runtime-profile/`.
- **Workspace SQL:** query, schede, tabelle, filtri e Metrics Board dell'app di base.
- **Analisi riproducibile:** inventario del bundle, dipendenze, metadati, hash e disassemblaggio LLDB.

Nel campione di ricerca sono stati verificati query SQLite, tre workspace
contemporanei, più schede SQL, tre filtri combinati e due Metrics Board.
Le modifiche sperimentali ai controlli locali sono opzionali e vincolate a un
eseguibile preciso; non attestano lo sblocco di ogni funzione Premium.

<p align="center">
  <img src="docs/images/sql-tabs.png" alt="Schede SQL multiple con il risultato di una query su dati sintetici" width="100%">
  <br><sub>Prova locale con più schede SQL. Le schermate mostrano esclusivamente dati sintetici.</sub>
</p>

## Compatibilità

| Componente | Stato |
|---|---|
| macOS su Apple Silicon, ARM64 | Verificato su macOS **27.0.1**, build **26A434** |
| Versione TablePlus | **27.0.2**, build **818**, verificata localmente; altre build ammesse per il branding se superano il controllo delle risorse, con avvio da verificare sul Mac di destinazione |
| Modifiche ai controlli locali | Solo **27.0.2 (818)**, con SHA-256 esatto |
| macOS 12 e successivi | Minimo dichiarato dal bundle di base; le altre versioni non sono state provate |
| Mac Intel / Rosetta | Slice presente nell'app originale; modifiche ai controlli locali e runtime non verificati |
| Windows, Linux e web | Nessuna implementazione in questo repository |
| Database | SQLite verificato; gli altri adattatori del bundle non sono stati provati end-to-end |
| AI, MCP e servizi online | Componenti individuati; integrazioni e autorizzazioni lato server non verificate |
| Strumenti | Python **3.9+**, zsh e strumenti macOS di copia/firma; strumenti sviluppatore Apple per l'analisi opzionale |

## Installazione

Occorre avere TablePlus installato separatamente in `/Applications/TablePlus.app`.
Il setup predefinito verifica le risorse necessarie per nome e icona anche su
altre build. Il vincolo di versione e hash esatti riguarda `--local-controls`.
Non scarica l'applicazione. La build 802 non è stata provata end-to-end qui.

1. Scarica o clona questo repository e apri la sua cartella nel Terminale.
2. Controlla l'ambiente senza creare o modificare la copia:

   ```sh
   ./scripts/setup_tablecraft.sh --check
   ```

3. Crea la copia con nome e grafica TableCraft:

   ```sh
   ./scripts/setup_tablecraft.sh
   ```

4. Avvia TableCraft:

   ```sh
   ./"Avvia TableCraft.command"
   ```

È possibile anche aprire direttamente `Avvia TableCraft.command`: al primo avvio
esegue automaticamente il setup, se sono presenti i requisiti indicati sopra.
Il file ZIP di GitHub non include l'applicazione preparata.

Il setup conserva l'installazione originale e non sovrascrive una copia locale
già esistente. La copia usa una firma ad hoc, distinta dalla firma Developer ID
originale. Gli aggiornamenti automatici della copia sono disabilitati.

Opzioni di ricerca, modalità offline e fixture SQL: [docs/setup.md](docs/setup.md).

## Come è organizzato

| Percorso | Contenuto |
|---|---|
| `scripts/` | Setup, branding, icone, analisi e verifica dei file pubblicabili |
| `assets/icons/` | PNG, ICNS e provenienza dell'illustrazione originale |
| `docs/` | Installazione, architettura, demo e pubblicazione |
| `analysis/` | Bundle locale, profili, backup ed evidenze; esclusi da Git |

La CI verifica sintassi, collegamenti locali e contenuto tracciato. Non compila
TablePlus e non certifica il funzionamento completo dell'app.

## Contribuire

Consulta [CONTRIBUTING.md](CONTRIBUTING.md), il [changelog](CHANGELOG.md) e le
[note per GitHub](docs/publishing.md). Non allegare credenziali, connessioni
esportate o screenshot di ambienti reali alle issue.

## Crediti e licenza

Il codice originale del repository è distribuito con licenza [MIT](LICENSE).
La licenza non si estende a TablePlus o alle sue risorse: vedi [NOTICE](NOTICE).
L'icona è stata generata con ImageGen; provenienza e asset sono descritti in
[docs/branding.md](docs/branding.md).

La presentazione prende come riferimento [PDFCraft](https://github.com/storytold/pdfcraft).
Il catalogo [awesome-reverse-engineering](https://github.com/morluto/awesome-reverse-engineering)
ha guidato la scelta degli strumenti di analisi. TableCraft è indipendente e
senza affiliazione con TablePlus, PDFCraft o ArtCraft.
