# Static Actor App Deployment

This document describes how to create deployable static builds of Cuemaster and LineRecorder for a normal webserver.

Both apps are browser-only React/Vite applications. A deployment is just the app's built `dist/` directory copied to a webserver. There is no server-side runtime.

## Requirements

- Node dependencies installed in each app directory.
- A static webserver that serves HTML, JavaScript, CSS, and asset files.
- HTTPS for production use.

LineRecorder uses browser microphone APIs, so it must be served from a secure context. `https://` is the normal production answer. `http://localhost` works for local testing, but plain `http://` on a remote server should not be used.

Cuemaster and LineRecorder store imported packages and local app state in browser storage. The webserver does not store actor data.

## Output Directories

The build output directory for both apps is:

```text
dist/
```

For example:

```text
cuemaster/dist/
linerecorder/dist/
```

Deploy the full contents of each `dist/` directory, not the directory name itself unless that matches your intended URL layout.

## Recommended Build Command

Use the static build script for webserver deployment:

```sh
npm run build:static
```

This runs Vite with `--base=./`, which makes generated asset URLs relative. Relative asset URLs are the safest default because the app can be deployed at either a domain root or a subdirectory.

Examples:

```text
https://example.org/cuemaster/
https://example.org/linerecorder/
```

or:

```text
https://cuemaster.example.org/
https://linerecorder.example.org/
```

## Build Cuemaster

From the repository root:

```sh
cd cuemaster
npm install
npm run test
npm run build:static
```

Deploy:

```text
cuemaster/dist/index.html
cuemaster/dist/assets/
```

If deploying under `/cuemaster/`, copy the contents of `cuemaster/dist/` to the server's `cuemaster/` directory.

Example final layout:

```text
webroot/
  cuemaster/
    index.html
    assets/
```

## Build LineRecorder

From the repository root:

```sh
cd linerecorder
npm install
npm run test
npm run build:static
```

Deploy:

```text
linerecorder/dist/index.html
linerecorder/dist/assets/
```

If deploying under `/linerecorder/`, copy the contents of `linerecorder/dist/` to the server's `linerecorder/` directory.

Example final layout:

```text
webroot/
  linerecorder/
    index.html
    assets/
```

## Combined Webroot Example

One server can host both apps side by side:

```text
webroot/
  cuemaster/
    index.html
    assets/
  linerecorder/
    index.html
    assets/
```

Build and stage both apps:

```sh
cd cuemaster
npm install
npm run test
npm run build:static
cd ../linerecorder
npm install
npm run test
npm run build:static
```

Then copy:

```text
cuemaster/dist/*     -> webroot/cuemaster/
linerecorder/dist/*  -> webroot/linerecorder/
```

Use your host's normal upload mechanism: Cloudflare Workers & Pages, `rsync`, `scp`, SFTP, Netlify, or a manual file upload.

If dependencies are already installed, `npm install` can be skipped. The important deploy artifact is the result of `npm run build:static`.

## Local Preview

Preview the production build before uploading it:

```sh
cd cuemaster
npm run build:static
npm run preview
```

Cuemaster previews on the configured Vite preview port, normally `http://127.0.0.1:4173/`.

```sh
cd linerecorder
npm run build:static
npm run preview
```

LineRecorder's preview script uses port `5174`, so the local preview URL is normally `http://127.0.0.1:5174/`.

## Webserver Configuration

These apps currently use hash-free single-page-app routing lightly enough that static file serving is usually sufficient. If a future route is added and direct deep links must work, configure the server to serve `index.html` as the fallback for unknown paths under each app directory.

Recommended headers:

```text
Content-Type: correct MIME type for .html, .js, .css, .wasm if present
Cache-Control for index.html: no-cache
Cache-Control for assets/: public, max-age=31536000, immutable
```

The built asset filenames include hashes, so long caching is fine for files under `assets/`. Keep `index.html` fresh so users get new asset references after a deployment.

## Smoke Test After Deployment

Cuemaster:

1. Open the deployed Cuemaster URL.
2. Import a local `.playbook.zip` file.
3. Confirm the role list appears.
4. Start a rehearsal line.
5. Toggle stage directions and blocking if the Playbook contains them.
6. Refresh the page and confirm the imported Playbook remains available.

LineRecorder:

1. Open the deployed LineRecorder URL over HTTPS.
2. Import a Recording Request zip.
3. Confirm the requested lines appear.
4. Start the microphone.
5. Record and play a short take.
6. Accept the take.
7. Export recordings and confirm a zip downloads.

## Package Files For Actors

The hosted apps do not fetch production data automatically. Actors still need package files:

- Cuemaster consumes a Playbook zip from Stager.
- LineRecorder consumes a Recording Request zip from Stager.
- LineRecorder exports a role recordings zip for Stager import.

Typical Stager commands:

```sh
./main playbook --play fairies --audio-format mp3
./main recording-request --play fairies --role LILLIAN
```

Upload the resulting zip files to email, Google Drive, Dropbox, or another shared folder.

## Command-Line Cloudflare Deployment

After the Cloudflare Pages projects exist, deployment does not need to use the manual dashboard upload. Set a Cloudflare API token and account id in the environment, then run:

```sh
CLOUDFLARE_ACCOUNT_ID=<account-id> CLOUDFLARE_API_TOKEN=<token> scripts/deploy_webapps_to_cloudflare.sh
```

The script builds `cuemaster/dist/` and `linerecorder/dist/`, then deploys each folder with Wrangler direct upload. Use these variables if your Cloudflare project names differ from the local folder names:

```sh
CUEMASTER_PROJECT_NAME=my-cuemaster LINERECORDER_PROJECT_NAME=my-linerecorder scripts/deploy_webapps_to_cloudflare.sh
```

## Notes

- Use `npm run build` instead of `npm run build:static` only when the app will be served from the webserver root and absolute asset paths are desired.
- Do not deploy the Vite dev server for actors.
- Do not put Recording Request zips, Playbook zips, or exported recordings inside the app `dist/` directory unless intentionally publishing those files.
- LineRecorder microphone access may fail if the deployed page is inside an iframe or served without HTTPS.

## Deploying to Cloudflare Pages
The first time you start Cloudflare, choose the option to upload a folder. Choose LineRecorder or Cuemaster's `dist` folder. Do not accept the autogenerated name; use `cuemaster` or `linerecorder` as appropriate.

To add an app later, go to `Build/Workers & Pages` and select `Create Application`, `Upload your static files`, select the app's `dist` folder, set the worker name to the app name, and deploy.

The apps will then be available on Cloudflare as, for example:

- https://linerecorder.phil-surette.workers.dev/
- https://cuemaster.phil-surette.workers.dev/

Then share Playbook and Recording Request zips with actors separately.
