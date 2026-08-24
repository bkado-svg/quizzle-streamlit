# Quizzle Streamlit

A native Streamlit rebuild of Quizzle with teacher, student, and administrator views.

## Local use

```bash
pip install -r requirements.txt
streamlit run app.py
```

The first launch seeds an administrator account (`admin@quizzle.app` / `Admin123!`) and a demonstration teacher (`teacher@quizzle.app` / `Teacher123!`). Change these passwords after first sign-in.

## Academic catalogue data

The licensed-university register in `data/nuc_universities.json` was retrieved from the National Universities Commission lists for federal/public, state, and private universities on 24 August 2026. Faculty/discipline and programme options use the NUC Core Curriculum and Minimum Academic Standards (CCMAS) national baseline. The seeded Computer Science course catalogue is transcribed from the NUC Computing CCMAS global course structure. An institution may offer only a subset of the national CCMAS programmes, so Quizzle labels the programme data as a national baseline rather than claiming institution-specific accreditation.

## Deployment

Deploy `app.py` from this repository on Streamlit Community Cloud. SQLite is suitable for demonstrations; configure an external persistent database before production use because Community Cloud filesystems may be replaced during redeployment.
