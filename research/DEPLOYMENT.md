# GitHub Pages deployment

Buildless HTML/CSS/JS and JSON live in `docs/`. Local and published sites use identical files.

1. In **Settings → Pages → Build and deployment**, choose **GitHub Actions**.
2. Merge a checked pull request into `main`, or run **Publish research website** manually from `main`.
3. Wait for checks and `deploy-pages` to succeed; the environment link is the verified published URL.
4. Inspect `/research.html`, Historical queries, and Methods. Relative paths support the repository subdirectory.

Pull requests run offline checks without publishing. Pages uses scoped `GITHUB_TOKEN`, Pages write permission, and OIDC; no stored API key. Failed checks prevent deployment.

For data updates: rebuild/validate API and Parquet data locally, run `export_web_data.py` then `run_research.py`, review coverage/findings, and commit. Deployment itself never calls NBA endpoints.

Switching from branch-folder publication to GitHub Actions is a one-time Pages setting. The same static files also work with existing `main`/`docs` publication; in that mode the supplied Pages workflow does not control the published artifact.
