"""GO-Starch EcoPack Analyzer - Flask backend (SQLite + PDF reports).
Each visitor gets a private workspace identified by a cookie, so many people can use
the same deployed site without seeing each other's data."""
import io, json, os, sqlite3, uuid, datetime
from flask import Flask, request, jsonify, render_template, make_response, g
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1_000_000
DB = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecopack.db"))
NUM = ["starch", "go", "gly", "water", "thick", "ts", "eb", "w0", "ww", "wf", "wvtr", "rs", "bw"]

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.execute("CREATE TABLE IF NOT EXISTS state(cid TEXT PRIMARY KEY, data TEXT NOT NULL, updated TEXT)")
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()

def get_cid():
    return request.cookies.get("cid") or uuid.uuid4().hex

def reply(resp, cid):
    resp = make_response(resp)
    resp.set_cookie("cid", cid, max_age=31536000, httponly=True, samesite="Lax")
    return resp

def clean(state):
    """Server-side validation of formulation records."""
    if not isinstance(state, dict) or not isinstance(state.get("f"), list) or len(state["f"]) > 200:
        raise ValueError("Invalid data")
    out = []
    for f in state["f"]:
        if not isinstance(f, dict) or not str(f.get("name", "")).strip():
            raise ValueError("Every formulation needs a name")
        r = {"id": f.get("id"), "s": 1 if f.get("s") else 0, "name": str(f["name"])[:100]}
        for k in NUM:
            v = f.get(k)
            if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0):
                raise ValueError(f"Invalid value for {k}")
            r[k] = v
        r["bd"] = [{"d": b["d"], "w": b["w"], "n": str(b.get("n", ""))[:200]}
                   for b in f.get("bd", []) if isinstance(b.get("d"), (int, float)) and isinstance(b.get("w"), (int, float))]
        out.append(r)
    return {"f": out}

@app.route("/")
def index():
    return reply(render_template("index.html"), get_cid())

@app.route("/api/state", methods=["GET", "POST"])
def state():
    cid = get_cid()
    if request.method == "POST":
        try:
            data = clean(request.get_json(force=True))
        except Exception as e:
            return jsonify(error=str(e)), 400
        db().execute("REPLACE INTO state VALUES (?,?,?)", (cid, json.dumps(data), datetime.datetime.utcnow().isoformat()))
        db().commit()
        return reply(jsonify(ok=True), cid)
    row = db().execute("SELECT data FROM state WHERE cid=?", (cid,)).fetchone()
    return reply(jsonify(json.loads(row[0]) if row else None), cid)

def cls(r):
    return "-" if not r else "Conductive" if r < 1e4 else "Dissipative" if r <= 1e11 else "Insulative"

@app.route("/report.pdf")
def report():
    cid = get_cid()
    row = db().execute("SELECT data FROM state WHERE cid=?", (cid,)).fetchone()
    forms = json.loads(row[0])["f"] if row else []
    ss = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    fx = lambda v, d=1: "-" if v is None else f"{v:.{d}f}"
    head = ["Formulation", "Starch g", "GO g", "Gly g", "Water g", "GO/starch %", "Thick mm", "TS MPa", "EB %", "Water abs %", "Solub %", "Rs ohm/sq", "Class", "Biodeg %"]
    rows = [head]
    for f in forms:
        g_ = f["go"] / f["starch"] * 100 if f.get("starch") else 0
        wa = (f["ww"] - f["w0"]) / f["w0"] * 100 if f.get("w0") and f.get("ww") else None
        ws = (f["w0"] - f["wf"]) / f["w0"] * 100 if f.get("w0") and f.get("wf") else None
        loss = (f["bw"] - f["bd"][-1]["w"]) / f["bw"] * 100 if f.get("bw") and f["bd"] else None
        rows.append([Paragraph(f["name"] + (" (SAMPLE)" if f["s"] else ""), ss["BodyText"]), f["starch"], f["go"], f["gly"], f["water"],
                     fx(g_), fx(f.get("thick"), 2), fx(f.get("ts")), fx(f.get("eb"), 0), fx(wa), fx(ws),
                     "-" if not f.get("rs") else f"{f['rs']:.1e}", cls(f.get("rs")), fx(loss)])
    t = Table(rows, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5e9")), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#b7c9b0")),
                           ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    rec = request.args.get("rec", "")[:1500] or "Open the Dashboard module to generate a recommendation."
    story = [Paragraph("GO-Starch EcoPack Analyzer - Experimental Summary", ss["Title"]),
             Paragraph(f"Generated {datetime.date.today().isoformat()}. Entries marked SAMPLE are demonstration data, not laboratory measurements.", ss["BodyText"]),
             Spacer(1, 8), t, Spacer(1, 10), Paragraph("Recommendation", ss["Heading2"]), Paragraph(rec.replace("&", "&amp;").replace("<", "&lt;"), ss["BodyText"]),
             Paragraph("Method notes", ss["Heading2"]),
             Paragraph("Water absorption = (Wwet - Wdry)/Wdry x 100. Solubility = (W0 - Wdry after)/W0 x 100. Weight loss = (Initial - Final)/Initial x 100. "
                       "Conductive < 1e4, dissipative 1e4-1e11, insulative > 1e11 ohm/sq. Scores compare only the entered data.", ss["BodyText"])]
    doc.build(story)
    resp = make_response(buf.getvalue())
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = "attachment; filename=GO-Starch-EcoPack-Report.pdf"
    return resp

@app.route("/health")
def health():
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
