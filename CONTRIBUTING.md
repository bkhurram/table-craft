# Contribuire a TableCraft

Le modifiche possono riguardare setup, branding, analisi statica e documentazione.
Descrivere il comportamento prima e dopo, indicare macOS, architettura e versione
dell'app sorgente e usare dati sintetici per le prove.

## Verifiche locali

Il Makefile raccoglie i comandi di sviluppo (`make help` mostra l'elenco).
Per eseguire tutti i controlli e i test:

```sh
make check
make test TEST_PATTERN=test_installer.py
```

`make check-public` legge l'indice Git: aggiungere esplicitamente i file da
pubblicare prima di usarlo per verificare nuove modifiche. `make clean` elimina
solo le cache Python in `scripts/` e `tests/`.

Gli stessi controlli si possono eseguire direttamente:

```sh
python3 -m compileall -q scripts tests
python3 -m unittest discover -s tests -v
zsh -n scripts/python_runtime.sh
zsh -n scripts/setup_tablecraft.sh
zsh -n scripts/install_craft_icon.sh
zsh -n "Avvia TableCraft.command"
git add .
python3 scripts/check_public_repo.py
git diff --cached --check
```

Per modifiche a NIB o codice, documentare il campione esatto e verificare avvio,
titoli e comportamento interessato sulla copia locale. Non modificare
l'installazione originale durante le prove. Non dichiarare supporto per una
piattaforma o funzione senza una verifica corrispondente.

Il runtime previsto è incluso soltanto nelle parti verificate di `runtime-seed/`.
Per aggiornarlo, verificare `runtime/`, spostare il vecchio seed in un backup
locale e usare `make seed`, poi provare ripristino e packaging in un clone pulito.
Aggiungere tutte le nuove parti e il manifest allo stesso commit.
Non includere altri bundle, connessioni, credenziali o report grezzi. Issue e pull request devono contenere solo errori redatti e screenshot
sintetici. La CI non sostituisce la revisione manuale delle immagini.
