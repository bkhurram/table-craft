# Installazione e uso locale

## Requisiti

- Mac Apple Silicon, avviato nativamente in ARM64.
- Python 3.9 o successivo. È compatibile anche Python 3.9.6 fornito dagli
  strumenti sviluppatore Apple; non è necessario installare Python 3.11.
- Strumenti macOS `codesign`, `ditto`, `plutil` e `PlistBuddy`.
- TablePlus installato separatamente. Il setup predefinito controlla la
  compatibilità dei NIB e delle stringhe di branding prima di copiare l'app.
- Il campione storico TablePlus 27.0.2 (818) ha SHA-256:
  `4547216d88fcd2868e48f31a2079da27850ace793ae79cc0fb7963d9c827c05a`.
  Questo hash e questa versione sono obbligatori solo per `--local-controls`.
  La versione 26.10.22 (802) può usare il setup predefinito se le sue risorse
  superano i controlli; il suo avvio non è stato verificato qui.

`./scripts/setup_tablecraft.sh --check` esegue i controlli senza creare la copia.
Se manca Python o uno degli strumenti richiesti, il controllo si interrompe e
indica il requisito mancante.

Il setup cerca Python nel `PATH`, nei percorsi standard Homebrew, nel framework
Python e in `/usr/bin/python3`. Per scegliere un interprete specifico:

```sh
TABLECRAFT_PYTHON=/usr/bin/python3 /bin/zsh scripts/setup_tablecraft.sh --check
```

Se non è disponibile alcun Python compatibile, installare Python 3 da
[python.org](https://www.python.org/downloads/macos/) e riprovare. Gli strumenti
di analisi statica opzionali richiedono separatamente gli strumenti sviluppatore
Apple; il setup predefinito non usa `xcrun` e non rigenera l'icona ICNS già inclusa.

## Creare la copia

Aprire `Avvia TableCraft.command`: al primo avvio esegue automaticamente il setup
usando `/Applications/TablePlus.app`, poi avvia la copia. Il file ZIP di GitHub
contiene gli script, non l'applicazione preparata. Restano necessari tutti i
requisiti elencati sopra. In caso di errore, risolvere il requisito indicato e
riaprire il launcher.

Per eseguire i due passaggi manualmente, dal Terminale nella cartella scaricata:

```sh
./scripts/setup_tablecraft.sh
./"Avvia TableCraft.command"
```

Un percorso sorgente diverso può essere specificato con:

```sh
./scripts/setup_tablecraft.sh --source /percorso/TablePlus.app
```

Il setup crea `analysis/copies/TablePlus-Research.app`. Il percorso tecnico
mantiene il nome storico; nome visibile, schermata iniziale e menu usano
TableCraft. L'identificatore è `com.tinyapp.TablePlus.Research`.

La copia viene preparata in una cartella temporanea e resa disponibile solo
dopo la verifica della firma. Un errore pulisce la copia temporanea e permette
di riprovare. Gli entitlement vengono conservati dalla firma esistente senza
dipendere dall'estrazione XML.

Se una vecchia versione del setup ha lasciato una copia incompleta, spostare
altrove soltanto `analysis/copies/TablePlus-Research.app` e riaprire il launcher.
Conservare sia il vecchio `analysis/runtime-profile` sia il profilo stabile. Un errore di versione o hash con
`--local-controls` richiede esattamente TablePlus 27.0.2 (818). Per applicare
soltanto nome e icona alle altre build, usare il setup senza tale opzione.
Se il controllo delle risorse fallisce, il formato non è gestito dal rebranding
attuale: la procedura si interrompe prima di creare o modificare l'app.

Il profilo stabile è `~/Library/Application Support/TableCraft/runtime-profile/`.
Il vecchio `analysis/runtime-profile/` viene copiato automaticamente al primo
avvio, solo se il percorso stabile non esiste, e rimane conservato.
Il launcher imposta `CFFIXED_USER_HOME` per questo processo. Non importare profili
reali per le demo pubbliche. Il setup senza `--update` non sovrascrive copie già presenti e non
elimina i profili esistenti.

La copia è firmata ad hoc. L'app originale non viene modificata; la copia non
conserva l'identità Developer ID o la notarizzazione originale. Il setup non
modifica Gatekeeper, SIP o le impostazioni di sicurezza del Mac.

## Aggiornare conservando le connessioni

Chiudere TableCraft e, dalla cartella del progetto, eseguire:

```sh
./scripts/setup_tablecraft.sh --check
./scripts/setup_tablecraft.sh --update
./"Avvia TableCraft.command"
```

Il branding supporta 27.0.2 (818) e 27.1.0 (830). Nella 830 manca
`AboutWindow.nib`: viene aggiornata la risorsa Welcome presente, conservando
il supporto alla risorsa About della 818. Non servono nuove modifiche al codice
macchina. Risultati effettivi e limiti: [compatibilità](compatibility.md).

`--update` prepara e firma la nuova copia prima di sostituire quella attiva.
Conserva la vecchia app in `analysis/copies/previous.*/TablePlus-Research.app`
e una copia completa del profilo in `profile-backups/` accanto al profilo stabile.
Un errore durante la preparazione lascia attiva la vecchia app. Se lo scambio
fallisce, il cleanup tenta di rimettere al suo posto il bundle precedente.
La procedura richiede che la copia sia chiusa e che sia disponibile il controllo
dei processi. Non riporta modifiche sperimentali ai controlli di licenza.
`--update --local-controls` viene rifiutato.

Il launcher mantiene `com.tinyapp.TablePlus.Research` e `CFFIXED_USER_HOME`
tra le versioni. Per scegliere un altro profilo, impostare un percorso assoluto:

```sh
TABLECRAFT_PROFILE="/percorso/assoluto/profilo" ./"Avvia TableCraft.command"
```

Se un percorso stabile esiste già, ha precedenza anche se vuoto: non viene
sovrascritto né unito al vecchio profilo. Se mancano connessioni, chiudere l'app,
conservare entrambi i profili e verificare quale contiene i file `Connections.plist`
e `ConnectionGroups.plist` sotto `Library/Application Support/`.
Per recuperare selettivamente connessioni usare l'import/export dell'app.
Non sovrascrivere file mentre l'app è aperta. Il profilo TablePlus originale
è distinto e non viene importato automaticamente.

I backup contengono dati privati: conservarli fuori dal repository pubblico.
Un ritorno alla versione precedente richiede anche un backup del profilo
compatibile; non è stata certificata la retrocompatibilità dei dati dopo
scritture della 830. Spostare una copia del backup in un nuovo percorso e
avviare il vecchio bundle con `CFFIXED_USER_HOME` impostato a quel percorso,
senza sovrascrivere il profilo corrente.

## Installare su un altro Mac e licenza

Il secondo Mac deve avere TablePlus installato e gli stessi requisiti del setup.
Il setup predefinito e l'aggiornamento applicano il branding e mantengono i
controlli di licenza del produttore. Per Premium occorrono licenza valida e
attivazione sul Mac di destinazione secondo le condizioni del produttore.
Nella prova sulla 830 l'app mostra free trial e limita il ripristino a due filtri.
Non è stato disponibile un secondo Mac per certificare l'attivazione.

Per trasferire le connessioni usare l'export/import dell'app; migrare separatamente
password nel Portachiavi, chiavi SSH, certificati e database locali. Copiare
il solo repository non trasferisce il profilo. Nessun test qui prova accesso
a database remoti, servizi AI/MCP o credenziali su una seconda macchina.

## Controlli locali sperimentali

### Schede e workspace sulla build 830

Per TablePlus **27.1.0 (830)**, sul campione ARM64 con SHA-256
`8e18e7010a4714e8e8e900db2cb9e82f876438b6936d5d7b9fa2db679d895ef7`:

```sh
./scripts/setup_tablecraft.sh --check --workspace-limits
./scripts/setup_tablecraft.sh --update --workspace-limits
./"Avvia TableCraft.command"
```

Chiudere prima TableCraft. L'aggiornamento salva profilo e app precedente.
Alla prima installazione omettere `--update`. L'opzione applica otto modifiche
alla sola slice ARM64: sette rami sul numero di schede/workspace e il controllo
secondario delle schede. Non modifica stato licenza, filtri, Metrics Board o
autorizzazioni dei server database. Non c'è stato un limite al numero totale
di accessi identificato: il blocco osservato riguarda i workspace simultanei.

Verifica locale del 20 ottobre 2026: quattro schede SQL, query nella quarta
con risultato `tab_4 / 5`, tre workspace SQLite simultanei su dati sintetici,
con rete bloccata e profilo di prova separato. Manifest e disassemblati restano
in `analysis/evidence/limits-830/`. Queste prove non certificano gli altri
adattatori database. Un successivo `--update` senza `--workspace-limits`
ripristina i controlli originali; altre build vengono rifiutate prima di copiare.

### Campione storico 818

Il setup predefinito applica nome e grafica. Per includere le modifiche ai
controlli locali del campione di ricerca, durante la prima creazione:

```sh
./scripts/setup_tablecraft.sh --local-controls
```

L'opzione applica 21 sostituzioni di codice alla slice ARM64 del campione
supportato. La slice Intel resta invariata. Il manifest dei byte modificati è
scritto in `analysis/evidence/feature-controls/patch-manifest.json` e rimane locale.
Non vengono generate credenziali o autorizzazioni per servizi remoti.

I risultati multi-workspace, multi-tab, filtri e Metrics Board documentati nel
README provengono dalla copia sperimentale. Non costituiscono una garanzia per
ogni funzione del prodotto o per altri campioni.

## Modalità offline

```sh
./"Avvia TableCraft.command" --offline
```

La modalità usa `sandbox-exec` con rete bloccata e accesso negato ai Keychain e
ai percorsi TablePlus originali elencati nel profilo generato. È una modalità
di prova locale; non consente connessioni a database remoti e non è descritta
come isolamento completo. La disponibilità dipende da `sandbox-exec` sul Mac.

## Database di esempio

Creare un database SQLite nuovo con soli dati sintetici:

```sh
mkdir -p analysis/fixtures
sqlite3 analysis/fixtures/tablecraft-demo.sqlite < docs/demo.sql
```

In TableCraft, creare una connessione SQLite verso quel file. La query di
aggregazione restituisce kitchen 161.2, lighting 87.0 e stationery 102.0.

## Analisi statica opzionale

```sh
python3 scripts/analyze_tableplus.py /Applications/TablePlus.app
```

Il comando legge il bundle senza avviare i suoi eseguibili; usa `otool`, `nm`,
`strings`, `codesign`, `swift-demangle` e LLDB. Gli output restano sotto `analysis/`.
La scansione dei riferimenti con Capstone richiede l'ambiente opzionale:

```sh
python3 -m venv .venv-re
.venv-re/bin/pip install -r requirements-analysis.txt
.venv-re/bin/python scripts/find_feature_controls.py
```

## Ripristino

Chiudere TableCraft e avviare `/Applications/TablePlus.app` per usare l'installazione
originale. Conservare il profilo prima di spostare o rimuovere la cartella della
copia locale. Nessuna procedura del repository elimina automaticamente i dati.
