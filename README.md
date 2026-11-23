# GO-Starch EcoPack Analyzer

Flask + SQLite web app for a graphene oxide–starch antistatic eco-packaging film project (9 modules, PDF report).

## Project structure
```
ecopack/
├── app.py              # Flask backend: API, SQLite database, PDF report
├── templates/index.html# Frontend (all 9 modules, charts, animation)
├── requirements.txt    # Python packages
├── Procfile            # Start command for hosting platforms
└── ecopack.db          # Created automatically on first run
```

## 1. Run on your computer (5 minutes)
1. Install Python 3.10+ from python.org.
2. Open a terminal in the `ecopack` folder, then:
   ```
   python -m venv venv
   venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
   pip install -r requirements.txt
   python app.py
   ```
3. Open http://localhost:5000
4. Use the same Wi-Fi? Others can open `http://YOUR-PC-IP:5000` (for a quick classroom demo).

## 2. Make it accessible to everyone (free public link)

### Option A: PythonAnywhere (best for students, files stay saved)
1. Create a free account at pythonanywhere.com.
2. **Files** tab → upload the zip, open a **Bash console** and run `unzip ecopack.zip`.
3. In the console: `cd ecopack && pip install --user -r requirements.txt`
4. **Web** tab → *Add a new web app* → *Manual configuration* → Python 3.10+.
5. Set *Source code* to `/home/YOURNAME/ecopack`. Open the WSGI file and replace its contents with:
   ```python
   import sys
   sys.path.insert(0, '/home/YOURNAME/ecopack')
   from app import app as application
   ```
6. Click **Reload**. Your public link: `https://YOURNAME.pythonanywhere.com`

### Option B: Render.com (via GitHub)
1. Upload the folder to a new GitHub repository.
2. On render.com: *New → Web Service* → connect the repo.
3. Build command: `pip install -r requirements.txt`  Start command: `gunicorn app:app`
4. Deploy. You get `https://your-app.onrender.com`.
5. Warning: the free plan resets the disk on restart, so saved data can disappear. Add a paid persistent disk, or use Option A.

## 3. Make it downloadable
- **Source code:** upload to GitHub, then *Code → Download ZIP* gives anyone the full project.
- **Reports:** the Dashboard's **Download PDF report** button creates a PDF from the user's data.
- **Offline use:** run locally as in section 1. Charts need internet for the Chart.js library; to work fully offline, download `chart.umd.min.js` (Chart.js 4.4.1) into a `static/` folder and point the `<script>` tag in `templates/index.html` to `/static/chart.umd.min.js`.

## How data works
- Each visitor gets a private workspace (cookie `cid`), so many people can use one deployed site without seeing each other's records.
- Data is stored in SQLite (`ecopack.db`, table `state`) as JSON per visitor, and validated on the server.
- Demo entries are tagged SAMPLE. Use **Remove sample data** (Module 1) before entering real results.
- To change the database location, set the environment variable `DATABASE_PATH`.

## Using it for your capstone
- Real lab results → Modules 1, 4, 5, 6, 7 and the Dashboard.
- Modules 2, 3, 8 are educational/simulated and are labelled that way. Never present simulated values as measurements.
- Say honestly in your report that this is a data-analysis platform; your film experiments and DFT/xtb results are what feed it.
