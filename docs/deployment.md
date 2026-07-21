# Deployment

## Streamlit Community Cloud

1. Open Streamlit Community Cloud and create a new app.
2. Select `Utpal-Mishra/PRISM`.
3. Select the deployment branch, normally `main` after merge.
4. Set the entry point to `app/Home.py`.
5. Use Python 3.12 where available.
6. Add future secrets through the platform settings, never Git.
7. Deploy and verify the sample-data and upload workflows.

## Docker

```bash
docker build -t prism:v0.1.0 .
docker run -p 8501:8501 --env-file .env prism:v0.1.0
```

## Release gate

- CI passes
- No secrets committed
- README and CHANGELOG updated
- Sample data works
- Invalid uploads fail safely
