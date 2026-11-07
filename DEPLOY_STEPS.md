# Publishing the ASI Explorer on Streamlit Community Cloud

1. Create a free GitHub account and a new repository (public or private), for example `asi-explorer`.
2. Upload the *contents* of this folder to the repository (GitHub web page: Add file > Upload files; or git).
   Files above 100 MB are rejected by GitHub - the notebook warned about any such file.
3. Open https://share.streamlit.io, sign in with GitHub, choose New app, select the repository, branch `main`,
   main file `app.py`, and pick the address you want (for example `asi-emissions`). Deploy.
4. In the app's Settings > Secrets add (TOML format):
       ASI_APP_PASSWORD = ""                       # empty = open to everybody
       ASI_DATASET_URL  = "https://zenodo.org/..." # permanent address of the ZIP of the results folder
5. The address `https://<chosen-name>.streamlit.app` is permanent. A free app that nobody has visited for a
   while goes to sleep and wakes up at the next visit (about a minute); the address itself does not change.

Memory: the free host provides about 2.7 GB; this bundle needs roughly 119 MB when loaded.
Image export: `packages.txt` installs Chromium for PNG/JPG export; if the host refuses it, the chart toolbar's camera icon still saves PNG.
