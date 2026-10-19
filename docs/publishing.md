# Preparare e pubblicare su GitHub

Il repository pubblico deve contenere soltanto script originali, documentazione,
icona generata e schermate con dati sintetici. Bundle, profili, backup, chiavi
ed evidenze grezze restano locali. `.gitignore` esclude questi percorsi;
`check_public_repo.py` verifica anche il contenuto effettivamente nell'indice Git.

## Controllo prima del commit

```sh
git add .
python3 scripts/check_public_repo.py
git diff --cached --stat
git diff --cached --check
```

Rivedere il diff e le immagini. Il controllo automatico intercetta percorsi
privati e alcuni formati di credenziali, ma non riconosce ogni possibile dato
sensibile. Le schermate incluse sono state selezionate dalle prove SQLite
sintetiche; le schermate della schermata iniziale con connessioni reali sono escluse.

## Commit e remote

Il progetto usa il branch locale `main`. Dopo la revisione:

```sh
git commit -m "Prepare TableCraft repository"
```

Il remote locale rilevato è `git@github.com:bkhurram/table-craft.git`.
Controllare che `origin` corrisponda al repository e alla visibilità desiderati:

```sh
git remote -v
```

Dopo il commit e la verifica del remote:

```sh
git push -u origin main
```

Il lavoro di preparazione locale non effettua push e non crea release.

## Presentazione suggerita

- Nome repository configurato: `table-craft`; nome visibile dell'app: `TableCraft`.
- Descrizione: `Local TablePlus customization for macOS with Craft branding, an isolated profile and reproducible analysis tools.`
- Topic: `macos`, `database`, `sql`, `sqlite`, `developer-tools`, `customization`.
- Social preview: usare l'icona originale o una schermata con soli dati sintetici.

## Release

La CI non carica bundle o profili e non produce installatori. Una release del
repository può distribuire i sorgenti degli strumenti e gli asset originali;
il setup richiede un'app installata separatamente. Non presentare il progetto
come riscrittura indipendente o come parte della comunità ArtCraft.
