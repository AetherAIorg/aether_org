# Margin GitHub Pages Landing Site

Static landing page for the Margin / portfolio intelligence demos.

Production deploys are handled by the **[deployments](https://github.com/AetherAIorg/deployments)** repo (`deploy-pages.yml`). Pushes to `main` here trigger that pipeline via [`trigger-deploy.yml`](.github/workflows/trigger-deploy.yml).

## Local Preview

Open `index.html` directly in a browser, or run:

```bash
python3 -m http.server 8080
```

Then visit `http://localhost:8080`.

## GitHub Pages (manual fallback)

1. Create a repo for the landing page, for example `margin`.
2. Put the contents of this folder at the repo root.
3. In GitHub, go to **Settings → Pages**.
4. Set source to `Deploy from a branch`.
5. Choose `main` and `/root`.
6. Your site will be available at `https://<username>.github.io/<repo>/`.

If you name the repo `<username>.github.io`, GitHub Pages will serve it at `https://<username>.github.io/`.
