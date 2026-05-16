## Pharmacovigilance Signal Triage Copilot – Agent Inteligent pentru Prioritizarea Semnalelor de Siguranță în Medicamente
### Scop
Dezvoltarea unui agent AI capabil să analizeze volume mari de rapoarte de reacții adverse, să normalizeze datele, să identifice semnale timpurii de siguranță pentru combinații medicament–eveniment și să genereze automat pachete explicabile de evidențe pentru experții în farmacovigilență.

### Ideea de baza
Echipele de siguranță medicamentoasă (pharmacovigilance / PV) primesc de la mii până la milioane de rapoarte privind efectele adverse ale medicamentelor. Aceste rapoarte sunt frecvent incomplete, redundante, neuniforme și greu de procesat: denumirile medicamentelor variază (brand, generic, ortografie), descrierea reacțiilor diferă de la raport la raport, iar cazurile pot fi duplicat sau lipsite de context. Procesul actual de triaj necesită multă muncă manuală: specialiștii trebuie să curețe datele, să verifice semnalele potențiale și să compileze evidențe înainte ca experții să ia o decizie. Când triajul este lent sau supraîncărcat, semnalele critice pot fi identificate prea târziu, ceea ce crește riscul pentru pacienți și costurile pentru industrie. Pharmacovigilance Signal Triage Copilot își propune să acționeze ca un „detector de fum” pentru siguranța medicamentelor:

* identifică devreme semnale neobișnuite medicament–eveniment explică motivele pentru care au fost detectate pregătește automat un pachet de evidențe pentru revizuire oferă o listă prioritizată a semnalelor

* Deciziile finale rămân la experți, dar aceștia pornesc de la un top inteligent și contextualizat, nu de la o masă dezorganizată de rapoarte.

### TODOlist: 
Sistemul inteligent trebuie să fie capabil să acopere funcționalități, precum:

* Selectarea unui medicament + interval de timp - filtrarea datelor privind reacțiile adverse în funcție de cerințele utilizatorului.
* Identificarea celor mai importante semnale medicament–eveniment - calcularea unor metrici standard de disproporționalitate, precum PRR (Proportional Reporting Ratio) sau ROR (Reporting Odds Ratio).
* Analiza trendului comparativ cu un baseline - detectarea creșterilor semnificative în timp pentru anumite evenimente.
* Explorarea rapoartelor individuale - funcționalitate de drill‑down pentru a vizualiza cazuri reprezentative.
* Generarea unui „Signal Packet” exportabil (PDF/slide) - pachet gata de prezentat, incluzând: descrierea semnalului, justificare, grafice cifre relevante, exemple de rapoarte.
* Ranking simplu al semnalelor - pe baza unor criterii precum severitatea evenimentelor + creșterea în timp.
* Normalizarea avansată a denumirilor medicamentelor (brand → INN).
* Normalizarea termenilor pentru reacțiile adverse (ex.: MedDRA).
* Deduplicare automată a cazurilor suspecte.
* Explicații generate de LLM pentru fiecare semnal.
* Detectarea semnalelor emergente cu rate neobișnuite față de istoricul medicamentului.
* Recomandări AI pentru prioritizarea investigațiilor.
### Evaluare / KPI-uri sugerate
* Reducerea timpului de triaj comparativ cu analiza manuală.
* Numărul de „signal packets” generate per analist per zi.
* Timp mai scurt de la apariția semnalului până la revizuire (proxy pentru detecție timpurie).
* Grad de standardizare al pachetelor generate automat.
### Bibliografie
* Primary PV data 
    * openFDA FAERS API: https://open.fda.gov/apis/drug/event/ 
    * FAERS background: https://www.fda.gov/drugs/questions-and-answers-fdas-adverse-event-reporting-system-faers/fda-adverse-event-reporting-system-faers-public-dashboard 
* Drug normalization + open drug data 
    * RxNorm: https://lhncbc.nlm.nih.gov/RxNorm/
    * DrugCentral (open drug database): https://drugcentral.org/ 
    * ChEMBL (bioactivity + compounds): https://www.ebi.ac.uk/chembl/ 
* Open Targets (target-disease associations): https://platform.opentargets.org/

### Optional safety-related sources
* FDA Recalls (open): https://open.fda.gov/apis/food/enforcement/ (useful pattern for “alerts/recalls” style) 
* PubMed E-utilities (literature): https://www.ncbi.nlm.nih.gov/books/NBK25501/

## Stage 2 (MVP) implemented: Signal Detection Engine

În acest stage, proiectul calculează semnale statistice pentru combinații medicament-eveniment și le ordonează după importanță.

### Ce calculează

- `PRR` (Proportional Reporting Ratio)
- `ROR` (Reporting Odds Ratio)
- `Chi-square` cu corecție Yates
- `valid_signal` folosind regula: `PRR >= 2`, `n >= 3`, `Chi² >= 4`
- `score` simplu pentru ranking (frecvență + severitate)
- trend lunar și flag `emerging` pentru creșteri bruște

### Structură modulară adăugată

- `app/baseline.py` — ia baseline global FAERS (total rapoarte + frecvențe pe evenimente)
- `app/signals.py` — formulele statistice și ordonarea semnalelor
- `app/trend.py` — agregare lunară și detecție trend/emergență
- `app/openfda.py` — helpere noi pentru count-uri agregate (`fetch_total_reports`, `fetch_count_buckets`)
- `app/runner.py` — integrare CLI pentru stage 2

### Cum rulezi stage 2

Din rădăcina proiectului:

```bash
python -m app.runner --drug ibuprofen --start 2024-01-01 --end 2024-03-31 --stage2 --top-signals 10
```

Output-ul este JSON și include:

- totaluri (`drug_total_reports`, `global_total_reports`)
- lista `signals` ordonată
- metrici (`prr`, `ror`, `chi_square_yates`, `score`, `valid_signal`)
- trend pentru fiecare semnal (`latest_month`, `growth_ratio`, `emerging`)