Pharmacovigilance Signal Triage Copilot – Agent Inteligent pentru Prioritizarea Semnalelor de Siguranță în Medicamente
Scop
Dezvoltarea unui agent AI capabil să analizeze volume mari de rapoarte de reacții adverse, să normalizeze datele, să identifice semnale timpurii de siguranță pentru combinații medicament–eveniment și să genereze automat pachete explicabile de evidențe pentru experții în farmacovigilență.

Ideea de baza
Echipele de siguranță medicamentoasă (pharmacovigilance / PV) primesc de la mii până la milioane de rapoarte privind efectele adverse ale medicamentelor. Aceste rapoarte sunt frecvent incomplete, redundante, neuniforme și greu de procesat: denumirile medicamentelor variază (brand, generic, ortografie), descrierea reacțiilor diferă de la raport la raport, iar cazurile pot fi duplicat sau lipsite de context. Procesul actual de triaj necesită multă muncă manuală: specialiștii trebuie să curețe datele, să verifice semnalele potențiale și să compileze evidențe înainte ca experții să ia o decizie. Când triajul este lent sau supraîncărcat, semnalele critice pot fi identificate prea târziu, ceea ce crește riscul pentru pacienți și costurile pentru industrie. Pharmacovigilance Signal Triage Copilot își propune să acționeze ca un „detector de fum” pentru siguranța medicamentelor:

identifică devreme semnale neobișnuite medicament–eveniment explică motivele pentru care au fost detectate pregătește automat un pachet de evidențe pentru revizuire oferă o listă prioritizată a semnalelor

Deciziile finale rămân la experți, dar aceștia pornesc de la un top inteligent și contextualizat, nu de la o masă dezorganizată de rapoarte.

TODOlist
Sistemul inteligent trebuie să fie capabil să acopere funcționalități, precum:

Selectarea unui medicament + interval de timp - filtrarea datelor privind reacțiile adverse în funcție de cerințele utilizatorului.
Identificarea celor mai importante semnale medicament–eveniment - calcularea unor metrici standard de disproporționalitate, precum PRR (Proportional Reporting Ratio) sau ROR (Reporting Odds Ratio).
Analiza trendului comparativ cu un baseline - detectarea creșterilor semnificative în timp pentru anumite evenimente.
Explorarea rapoartelor individuale - funcționalitate de drill‑down pentru a vizualiza cazuri reprezentative.
Generarea unui „Signal Packet” exportabil (PDF/slide) - pachet gata de prezentat, incluzând: descrierea semnalului, justificare, grafice cifre relevante, exemple de rapoarte.
Ranking simplu al semnalelor - pe baza unor criterii precum severitatea evenimentelor + creșterea în timp.
Normalizarea avansată a denumirilor medicamentelor (brand → INN).
Normalizarea termenilor pentru reacțiile adverse (ex.: MedDRA).
Deduplicare automată a cazurilor suspecte.
Explicații generate de LLM pentru fiecare semnal.
Detectarea semnalelor emergente cu rate neobișnuite față de istoricul medicamentului.
Recomandări AI pentru prioritizarea investigațiilor.
Evaluare / KPI-uri sugerate

Reducerea timpului de triaj comparativ cu analiza manuală.
Numărul de „signal packets” generate per analist per zi.
Timp mai scurt de la apariția semnalului până la revizuire (proxy pentru detecție timpurie).
Grad de standardizare al pachetelor generate automat.
Bibliografie
Primary PV data • openFDA FAERS API: https://open.fda.gov/apis/drug/event/ • FAERS background: https://www.fda.gov/drugs/questions-and-answers-fdas-adverse-event-reporting-system-faers/fda-adverse-event-reporting-system-faers-public-dashboard Drug normalization + open drug data • RxNorm: https://lhncbc.nlm.nih.gov/RxNorm/ • DrugCentral (open drug database): https://drugcentral.org/ • ChEMBL (bioactivity + compounds): https://www.ebi.ac.uk/chembl/ • Open Targets (target-disease associations): https://platform.opentargets.org/

Optional safety-related sources • FDA Recalls (open): https://open.fda.gov/apis/food/enforcement/ (useful pattern for “alerts/recalls” style) • PubMed E-utilities (literature): https://www.ncbi.nlm.nih.gov/books/NBK25501/

Faze de dezvoltare
Faza 1 — Fundația datelor
Obiectiv: Să poți trage date din FAERS și să le curăți
Tasks:

Conectare la openFDA FAERS API
Filtrare după medicament + interval de timp
Normalizare nume medicamente via RxNorm (Advil → Ibuprofen)
Normalizare termeni reacții adverse (MedDRA basic)
Deduplicare cazuri suspecte

Output: O funcție care returnează date curate pentru un medicament dat

Faza 2 — Signal Detection Engine
Obiectiv: Să calculezi semnalele statistice
Tasks:

Calculare PRR (Proportional Reporting Ratio)
Calculare ROR (Reporting Odds Ratio)
Ranking semnale după severitate + frecvență
Detectare trend vs baseline istoric
Identificare semnale emergente (creșteri bruște)

Formule:
PRR = (n_drug_event / n_drug_total) / (n_all_event / n_all_total)

ROR = (n_drug_event / n_drug_no_event) / (n_other_event / n_other_no_event)

Semnal valid dacă: PRR ≥ 2, n ≥ 3, Chi² ≥ 4
Output: Listă ordonată de semnale cu scoruri

Faza 3 — LLM Explainer
Obiectiv: Claude explică fiecare semnal în limbaj natural
Tasks:

Prompt engineering pentru explicații clare
Generare justificare pentru fiecare semnal detectat
Recomandări AI pentru prioritizare investigații
Integrare opțională PubMed pentru citări

Exemplu output LLM:
Semnal: Ibuprofen → Insuficiență renală acută
PRR: 4.2 | ROR: 3.8 | Cazuri: 47

"Există un semnal statistic semnificativ între 
Ibuprofen și insuficiența renală acută. PRR de 4.2 
indică că acest eveniment este raportat de 4x mai 
frecvent față de alte medicamente. Trendul din 
ultimele 3 luni arată o creștere de 23%..."

Faza 4 — UI Dashboard
Obiectiv: Interfață pentru analistul PV
Componente UI:

Search bar: medicament + date range
Tabel semnale rankate cu filtre
Grafice trend în timp
Drill-down rapoarte individuale
Buton Export Signal Packet PDF


Faza 5 — Signal Packet Export
Obiectiv: PDF/slide gata de prezentat expertului
Conținut pachet:

Titlu semnal + medicament
Statistici PRR/ROR cu interpretare
Grafic trend temporal
Top 3-5 cazuri reprezentative
Explicație LLM
Recomandare prioritizare


Arhitectura tehnică recomandată
Frontend (React)
│
├── Dashboard principal
├── Signal Explorer
├── Report Viewer
└── Export Button
│
Backend (Python / FastAPI)
│
├── /api/search          → query FAERS
├── /api/signals         → calculează PRR/ROR
├── /api/explain         → LLM explanations
├── /api/export          → generează PDF
│
Data Layer
│
├── openFDA FAERS API
├── RxNorm API
└── Cache local (SQLite / JSON)
│
AI Layer
└── Claude API (Anthropic)