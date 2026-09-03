# Quizzle Streamlit

A native Streamlit rebuild of Quizzle with teacher, student, and administrator views.

## Local use

```bash
pip install -r requirements.txt
streamlit run app.py
```

The first launch seeds an administrator account (`admin@quizzle.app` / `Admin123!`) and a demonstration teacher (`teacher@quizzle.app` / `Teacher123!`). Change these passwords after first sign-in.

## Academic catalogue data

The licensed-university register in `data/nuc_universities.json` was retrieved from the National Universities Commission lists for federal/public, state, and private universities on 24 August 2026. Faculties use the NUC discipline structure, while the Department field contains organisational department names rather than degree-programme names. `data/nuc_courses.json` contains course structures extracted from all 17 NUC CCMAS discipline documents. Programme tables with irregular PDF layouts receive only frequently shared, verified courses from the same discipline and are marked `shared_discipline_baseline`. An institution may offer only a subset of the national CCMAS programmes, so Quizzle labels the programme data as a national baseline rather than claiming institution-specific accreditation.

`data/buk_academic_catalog.json` is the first university-specific catalogue. It records Bayero University Kano's 18 faculties and 93 academic departments from the university's 2023 Annual Report and assigns the university's official undergraduate programme names to their responsible departments. When Bayero University is selected, registration and course creation use this BUK catalogue instead of the generic NUC discipline hierarchy.

## Database integrity

Administrators can download the live SQLite database and `data/integrity_queries.sql` from the Administration page. The database includes reporting views for the university register, academic catalogue, teacher courses, quiz summaries, attempts, activity events, and shared resources. The SQL suite covers SQLite integrity, foreign keys, orphan records, uniqueness, required fields, hierarchy coverage, valid levels and semesters, score constraints, timestamp ordering, live-attempt duplication, activity durations, and representative view queries.

## Deployment

Deploy `app.py` from this repository on Streamlit Community Cloud. SQLite is suitable for demonstrations; configure an external persistent database before production use because Community Cloud filesystems may be replaced during redeployment.
