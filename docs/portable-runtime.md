# Runtime incorporato e pacchetto portabile

Il progetto locale include `runtime/TableCraft.app`: è una copia completa del
bundle personalizzato 27.1.0 (830), con eseguibili, framework, risorse e firma
ad hoc conservati. Il launcher preferisce questo runtime e non cerca TablePlus
in `/Applications`. Anche `setup_tablecraft.sh --check` verifica il runtime
incorporato senza richiedere l'app originale.

Il catalogo [awesome-reverse-engineering](https://github.com/morluto/awesome-reverse-engineering)
fornisce riferimenti agli strumenti di analisi; non è un decompilatore eseguibile.
L'integrazione conserva il codice nativo esistente: non produce il sorgente di
TablePlus né una sua implementazione indipendente compilabile.

## Da un repository pulito

Il repository include `runtime-seed/manifest.json` e tutte le parti
`runtime.zip.partNNN` (massimo 48 MiB ciascuna). Sono file Git normali: non
servono Git LFS, TablePlus installato o download da servizi esterni.
Su macOS Apple Silicon, con Python 3.9+ e Command Line Tools Apple:

```sh
make check-seed
make package
```

`make package` verifica un runtime esistente oppure ricompone il seed, verifica
i checksum, estrae in una cartella temporanea e controlla inventario, override e
firma prima di pubblicare `runtime/`. Poi genera
`dist/TableCraft-macos-arm64.zip` e `.sha256`. Per un percorso diverso:

```sh
make package OUTPUT=dist/TableCraft-altro.zip
```

Il ripristino conserva link relativi e permessi. Un runtime presente ma alterato
interrompe il comando e non viene sostituito. Un output ZIP già presente viene
rifiutato. `make bootstrap` ripristina senza esportare. `make clean` conserva
seed, runtime, ZIP e profili. Prevedere almeno 2 GB liberi per ripristino e packaging.

## Aggiornare il seed incluso

Chiudere l’app, preparare e verificare il nuovo `runtime/`, conservare il vecchio
`runtime-seed/` fuori dal percorso e poi eseguire:

```sh
make verify
make seed
make check-seed
```

Versionare insieme il manifest e tutte le parti, eliminando dall’indice le parti
precedenti non più presenti. Provare `make package` in una copia senza `runtime/`,
`analysis/`, `dist/` o ambienti Python locali. `make seed` rifiuta di sovrascrivere
il seed esistente. Il seed comprende solo bundle e manifest, senza profili o token.
Non nasce dal solo branding: mantiene il campione completo già personalizzato.

## Avvio

```sh
./"Avvia TableCraft.command"
```

Richiede macOS su Apple Silicon e Python 3.9+. L'opzione `--offline` e il profilo
stabile già usati dal launcher restano disponibili. Non servono un'installazione
di TablePlus, download, compilazione o una versione vendor compatibile sul Mac
di destinazione. Rimangono i requisiti macOS del bundle incorporato.

## Incorporazione e verifica

Per incorporare una copia già personalizzata in un checkout senza `runtime/`:

```sh
python3 scripts/portable_runtime.py embed
python3 scripts/portable_runtime.py verify
```

Il runtime usa il servizio `com.tablecraft.TableCraft` e l'etichetta `TableCraft`
per le password generiche. Per un runtime precedente già incorporato:

```sh
python3 scripts/portable_runtime.py isolate-keychain
```

L'operazione conserva un backup e non migra le password esistenti: vedi
[Portachiavi](keychain-isolation.md).

`embed` prende il bundle da `analysis/copies/TablePlus-Research.app`; `--source`
può selezionare un'altra copia personalizzata. Conserva il branding e gli override; se il servizio del Portachiavi è ancora
quello precedente, applica la separazione delle password prima della firma. Richiede la build 830 con tutti gli override già presenti e rifiuta di
sovrascrivere un runtime esistente. Le verifiche controllano:

- Identità TableCraft del Portachiavi e lunghezze Swift, quando presente nel manifest.
- Istruzioni ARM64 già modificate per schede, finestre, filtri e visibilità trial.
- Nome TableCraft, icona Craft e immagine interna uguali agli asset del progetto.
- SHA-256 e permessi di ogni file, directory e destinazioni dei link interni.
- Firma dell'applicazione e dei componenti annidati con `codesign`.

`runtime/manifest.json` registra l'inventario senza percorsi assoluti. Il launcher
lo verifica prima di preparare il profilo o avviare il processo. Un runtime
incompleto o alterato interrompe l'avvio: non attiva automaticamente il setup
con una versione differente. Il manifest rileva modifiche accidentali; non è
una firma di provenienza del distributore.

## Pacchetto completo

```sh
python3 scripts/portable_runtime.py package
```

Produce `dist/TableCraft-macos-arm64.zip` e un file `.sha256`. Lo ZIP
contiene una cartella `TableCraft-portable` con launcher, script, asset,
documentazione e runtime. Estrarla e aprire `Avvia TableCraft.command`.
Il contenuto viene verificato anche dopo la copia nella cartella di packaging.
Per una nuova esportazione scegliere `--output dist/un-altro-nome.zip`.

L'esportazione seleziona solo i file del prodotto: non include `.git`, ambienti
Python, analisi, database, connessioni o profili. Le connessioni già presenti sul
Mac continuano a usare il profilo stabile di TableCraft; trasferirle su un altro
Mac è un'operazione separata, come per le password del Portachiavi.

Il runtime conserva integralmente gli override esistenti. `--update` senza
`--source` viene fermato quando è presente il runtime incorporato. Per preparare
una nuova copia da un originale si può usare `setup_tablecraft.sh --source …`;
questa operazione non sostituisce il runtime incorporato. Per sostituirlo,
spostare prima `runtime/` in un backup e ripetere `embed` con una copia verificata.

## Repository e distribuzione

`runtime/`, `analysis/` e `dist/` restano generati e locali. Il repository e
lo ZIP sorgenti di GitHub includono invece `runtime-seed/`, che contiene tutti
i byte necessari per ricostruire il runtime senza dipendenze locali nascoste. Il codice degli strumenti resta MIT; i binari TablePlus conservano
la propria licenza e non diventano MIT. Questo comando non pubblica file né
carica il runtime su GitHub.

## Verifica eseguita il 20 ottobre 2026

- Analisi statica del runtime incorporato: 29 binari, nessun comando fallito.
- Tutti gli override richiesti presenti nel codice ARM64 e negli asset.
- 31 test automatici passati, inclusi integrità, rilocazione dei link, recupero
  del setup e controllo del runtime senza l'app originale.
- ZIP estratto in una cartella temporanea con spazi nel nome, verifica hash e
  firma superate; avvio nativo rimasto attivo durante la prova di 10 secondi,
  quindi terminato dal test. Profilo temporaneo separato, nessuna cartella
  `analysis/` o `.git` nel pacchetto.

Questa prova verifica il caricamento del runtime rilocato; non ripete le prove
GUI di query, schede e filtri documentate per il bundle originale. L'inventario
conferma che bundle incorporato e bundle personalizzato hanno lo stesso contenuto.

## Percorso MCP

L'eseguibile MCP del runtime è `runtime/TableCraft.app/Contents/MacOS/tablecraft-mcp`.
Per aggiornare un runtime incorporato precedente:

```sh
python3 scripts/portable_runtime.py rename-mcp
```

Il comando conserva un backup, aggiorna firma e manifest, e mantiene
`tableplus-mcp` come collegamento relativo per i riferimenti interni dell'app.
Le nuove incorporazioni usano già il nuovo nome. Nella configurazione del
client MCP, impostare il comando sul percorso assoluto di `tablecraft-mcp`.

Per aggiornare anche percorsi copiabili, etichette e testi delle impostazioni MCP
del campione supportato:

```sh
python3 scripts/portable_runtime.py brand-mcp-settings
```

La modifica aggiorna le stringhe e le rispettive lunghezze Swift nelle slice ARM64
e Intel, conserva un backup e rinnova firma e inventario. Non cambia protocolli,
permessi o la variabile di autenticazione `TABLEPLUS_MCP_ACCESS_TOKEN`. Riavviare
TableCraft per caricare i nuovi testi.

## Nome della registrazione MCP

Il nome passato ai client durante l'aggiunta automatica è `TableCraft`.
La rinomina dell'eseguibile non basta: il build 830 conserva il nome del server
in stringhe Swift separate, usate dalla configurazione MCP e dalle operazioni
di aggiunta, verifica e rimozione.

```sh
python3 scripts/portable_runtime.py brand-mcp-registration
```

Il comando supporta il runtime già aggiornato da `brand-mcp-settings`, verifica
SHA-256 e byte originali di entrambe le architetture, conserva un backup e
aggiorna firma e manifest. Le copie già corrette vengono riconosciute senza
modifiche. Riavviare TableCraft dopo l'aggiornamento.

Verifica del 21 ottobre 2026: 45 test superati; nuova registrazione eseguita dal
pulsante “Add to Codex” dopo la rimozione della sola voce MCP. L'app ha ricreato
`mcp_servers.TableCraft` con il comando `tablecraft-mcp`; la configurazione
risultante coincide con quella salvata prima della prova. Entrambi gli ZIP sono
stati estratti e verificati rispetto al runtime, con firma e override validi.

## Isolamento di porta, discovery e token MCP

```sh
python3 scripts/portable_runtime.py isolate-mcp
```

Per il runtime 830 già aggiornato con i comandi precedenti, questa operazione:

- Imposta `51013` come porta preferita predefinita di TableCraft; se occupata,
  l'allocatore conserva il comportamento di selezione di una porta libera.
- Limita il discovery del client nativo a `com.tinyapp.TablePlus.Research`,
  l'identificatore esistente e separato del bundle TableCraft. Non usa più i
  file di discovery di TablePlus o della versione Setapp.
- Separa il servizio portachiavi dei token MCP in `com.tablecraft.mcp.tokens`.
  Il servizio delle password delle connessioni resta `com.tablecraft.TableCraft`.
- Usa `tablecraft://integrations/start-mcp` per l'avvio automatico dell'app,
  evitando il protocollo URL `tableplus://`.

La generazione automatica del token deve restare attiva nelle impostazioni MCP.
Il client `tablecraft-mcp` legge porta e token correnti dal file locale
`~/Library/Application Support/com.tinyapp.TablePlus.Research/MCP/mcp-server.json`;
questo file viene prodotto dall'app con permessi `0600` e non viene incluso negli
ZIP. Non copiare il token nel repository o nella configurazione Codex.
La variabile `TABLEPLUS_MCP_ACCESS_TOKEN` resta compatibile per la modalità
manuale, quando si disattiva la generazione automatica.

L'aggiornamento non migra né modifica i token MCP di TablePlus. Eventuali token
manuali necessari a TableCraft devono essere creati nella sua nuova identità.
Dopo la modifica riavviare TableCraft e i client MCP già in esecuzione.

Verifica live del 21 ottobre 2026, con entrambe le app aperte:

- TableCraft su `127.0.0.1:51013`, TablePlus su `127.0.0.1:51004`.
- Richieste prive di token e token incrociati tra le due app rifiutati con HTTP
  `401`; token automatico TableCraft accettato con HTTP `200`.
- Il client nativo, avviato senza variabili per token manuali, completa
  `initialize`, `tools/list` e la lettura dei metadati delle connessioni salvate.
  La chiamata compare solo nell'audit di TableCraft. Nessun database viene aperto
  e nessuna query viene eseguita.
- Con `51013` occupata da un listener di test, TableCraft sceglie `51014` e il
  client recupera automaticamente la nuova porta e il token corrente. Rimossa
  l'occupazione e riavviata l'app, TableCraft torna a `51013`.
- 49 test automatici superati. Entrambe le architetture sono verificate
  staticamente; la prova live è eseguita su ARM64.

## Verifica da checkout pulito del 21 ottobre 2026

55 test automatici superati. Preparata una copia contenente soltanto i file
del repository e il nuovo seed, senza `runtime/`, `analysis/`, `dist/` o ambienti
Python locali. `make check-public check-seed package` ha ripristinato il runtime
e generato lo ZIP; dopo l’estrazione sono passati checksum SHA-256,
`make verify` e `make build`. Nello ZIP sono inclusi anche Makefile e test.
La prova verifica packaging e integrità; non ripete le prove GUI del database.
