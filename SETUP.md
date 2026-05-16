# Setup local

Acest ghid explică cum instalezi dependențele și cum rulezi aplicația local pe Windows.

## Cerințe

- Python 3.10+ instalat
- `pip` disponibil
- Acces la internet dacă vrei să rulezi modul live (openFDA / RxNorm)

## 1. Creează și activează mediul virtual

Deschide PowerShell în folderul proiectului și rulează:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Dacă PowerShell blochează activarea scripturilor, rulează o singură dată:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 2. Instalează dependențele

```powershell
pip install -r requirements.txt
```

Acest proiect folosește:

- `requests` pentru apeluri HTTP către openFDA și RxNorm
- `pytest` pentru teste

## 3. Rulează aplicația

### Mod demo

Modul demo folosește un record local și nu face apeluri la internet:

```powershell
python -m app.runner --demo --drug ibuprofen --start 2024-01-01 --end 2024-12-31
```

### Mod live

Modul live caută date în openFDA:

```powershell
python -m app.runner --drug ibuprofen --start 2024-01-01 --end 2024-01-31
```

### Cu normalizare RxNorm

Dacă vrei și normalizarea numelui medicamentului prin RxNorm:

```powershell
python -m app.runner --drug ibuprofen --start 2024-01-01 --end 2024-01-31 --normalize
```

### Parametri utili

- `--drug` este obligatoriu și reprezintă numele medicamentului
- `--start` și `--end` sunt obligatorii și acceptă formatul `YYYY-MM-DD` sau `YYYYMMDD`
- `--limit` controlează mărimea paginii pentru openFDA
- `--max-pages` limitează numărul de pagini descărcate, util la testare

## 4. Rulează verificările locale

Pentru testele simple ale proiectului:

```powershell
python -m pytest
```

Dacă `pytest` nu este disponibil în mediul activ, verifică mai întâi că ai instalat dependențele din `requirements.txt`.

## 5. Structura proiectului

- `app/openfda.py` - client openFDA și paginare
- `app/transform.py` - extragere și deduplicare cazuri
- `app/rxnorm.py` - normalizare opțională a medicamentelor
- `app/runner.py` - CLI principal
- `tests/` - teste unitare

## 6. Observații

- `venv/` nu trebuie urcat pe GitHub
- fișierele generate local, cache-urile și output-urile de rulare trebuie ignorate prin `.gitignore`
- pentru lucrul în echipă, păstrează în repo doar codul sursă, testele și documentația
