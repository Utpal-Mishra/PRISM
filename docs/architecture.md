# Architecture

```text
Streamlit UI
  -> loader and validator
  -> reporting metrics
  -> strategic observations
  -> charts and CSV exports
```

Week 1 deliberately separates interface, data, reporting, and configuration modules so forecasting, database storage, APIs, and authentication can be added without rewriting the application.
