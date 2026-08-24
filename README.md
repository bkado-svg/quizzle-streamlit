# Quizzle Streamlit

A native Streamlit rebuild of Quizzle with teacher, student, and administrator views.

## Local use

```bash
pip install -r requirements.txt
streamlit run app.py
```

The first launch seeds an administrator account (`admin@quizzle.app` / `Admin123!`) and a demonstration teacher (`teacher@quizzle.app` / `Teacher123!`). Change these passwords after first sign-in.

## Deployment

Deploy `app.py` from this repository on Streamlit Community Cloud. SQLite is suitable for demonstrations; configure an external persistent database before production use because Community Cloud filesystems may be replaced during redeployment.
