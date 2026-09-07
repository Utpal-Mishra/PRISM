# Deployment

## GitHub Pages — primary public application

PRISM's public application is browser-native and can be served directly from GitHub Pages.

### Repository configuration

1. Open the repository on GitHub.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, select **Deploy from a branch**.
4. Select branch **main**.
5. Select folder **/(root)**.
6. Save.

Expected URL:

```text
https://utpal-mishra.github.io/PRISM/
```

GitHub Pages requires the following root files from PRISM:

- `index.html`
- `assets/styles.css`
- `assets/app.js`
- `assets/prism.svg`
- `manifest.webmanifest`
- `404.html`
- `.nojekyll`

No build command or runtime server is required.

## Data handling

- Synthetic data is the default demonstration source.
- CSV files are parsed locally in the browser.
- XLS/XLSX files are read locally using the browser-loaded SheetJS library.
- Uploaded dataset contents are not posted to a PRISM application server by the GitHub Pages edition.

Do not interpret this architectural property as formal enterprise security approval. Confidential production deployment still requires approved hosting, identity, policy controls and security review.

## Local preview

```bash
python -m http.server 8000
```

Open `http://localhost:8000/`.

## Release gate

- Python CI passes for retained legacy/reference modules
- `node --check assets/app.js` passes
- `index.html` and static assets exist
- Synthetic demo loads
- CSV upload works locally
- XLSX upload works with CDN access
- No secrets are committed
- README and CHANGELOG are updated
- PR is promoted through `develop` before `main`

## Legacy Streamlit deployment

The historical Streamlit implementation remains in `app/` and `prism/` while the static edition stabilises. It is no longer required for the GitHub Pages deployment.
