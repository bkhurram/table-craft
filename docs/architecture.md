# Architettura e compatibilità verificata

## Ambito

La base storicamente analizzata è TablePlus 27.0.2 (818), bundle universale Intel/ARM64.
Il setup supporta anche 27.1.0 (830), verificata il 20 ottobre 2026 per branding,
firma, avvio, profilo e lettura SQLite: vedi [rapporto](compatibility.md).
L'analisi dettagliata e le prove funzionali sono state eseguite sulla slice
ARM64, su macOS 27.0.1 (26A434). Il minimo macOS 12.0 deriva dal plist del
campione e non rappresenta una prova su tutte le versioni intermedie.

TableCraft personalizza questa base localmente. Il repository non contiene
il sorgente del motore o dell'interfaccia TablePlus.

## Livelli osservati

| Livello | Evidenza statica |
|---|---|
| UI | AppKit, Swift/Objective-C, risorse NIB e localizzazioni |
| Contratti comuni | SQL.framework, SQLProtocol, SQLConnectionProtocol, QueryParams e risultati condivisi |
| Backend | Framework separati per SQLite, PostgreSQL, MySQL, MariaDB, Redis, Mongo e altri motori |
| Trasporto | Framework SSH separati e client HTTP |
| Estensioni | Componenti plugin, AI e MCP; eseguibile separato tableplus-mcp |
| Supporto | Sparkle, Sentry, componenti grafici e librerie Swift accessorie |

Sono stati inventariati due eseguibili principali e 27 framework. La presenza
di una dipendenza o di un endpoint nelle stringhe non dimostra l'uso a runtime
o il funzionamento completo di un'integrazione.

Nel metodo SQLite di esecuzione query, il disassemblaggio LLDB ha confermato
chiamate a `sqlite3_prepare_v2`, `sqlite3_step` e `sqlite3_finalize`.

## Personalizzazione

Il setup copia il bundle installato e assegna un identificatore distinto.
`rebrand_tablecraft.py` modifica risorse e testi visibili; gli oggetti stringa
NIB condivisi con `IBModuleName` sono duplicati per conservare i nomi Swift.
L'icona viene convertita in ICNS con gli strumenti nativi di macOS.

Le modifiche sperimentali al codice richiedono l'hash esatto del campione e sono
separate dal branding. Il profilo stabile risiede sotto `~/Library/Application Support/TableCraft/`,
indipendente dal checkout; il launcher migra per copia il vecchio profilo locale.
`--update` salva il profilo e conserva il bundle precedente.
I profili e le evidenze si generano localmente e non
fanno parte del contenuto Git.

## Limiti pratici

- SQLite è il backend provato end-to-end; gli altri database non sono certificati.
- AI, MCP e servizi remoti richiedono verifiche specifiche e, dove previsto, le proprie autorizzazioni.
- Intel, Rosetta e altre versioni macOS restano da provare.
- Non esistono port Windows, Linux o web in questo repository.
- La CI controlla gli strumenti e i file pubblici, non il prodotto vendor.

Riferimento metodologico: [awesome-reverse-engineering](https://github.com/morluto/awesome-reverse-engineering),
commit `29449628ed591065973ab8919a6df51ba254da82`. La raccolta iniziale ha usato
LLDB e gli strumenti nativi Apple; non una decompilazione completa in Ghidra.
