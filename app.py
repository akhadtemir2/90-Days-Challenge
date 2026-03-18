"""
Growth OS — Railway Production
"""
from flask import Flask, jsonify, request, Response
import json, os, shutil, logging, pathlib
from datetime import datetime, date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# Путь к папке с этим файлом — работает везде включая Railway
BASE_DIR   = pathlib.Path(__file__).parent.resolve()
TMPL_DIR   = BASE_DIR / "templates"
DATA_FILE  = BASE_DIR / "data.json"
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

app = Flask(__name__, template_folder=str(TMPL_DIR))
app.config["JSON_ENSURE_ASCII"] = False

# ── Data ─────────────────────────────────────────────────────────────────────
def load():
    if not DATA_FILE.exists():
        d = default_data(); save(d); return d
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"load error: {e}")
        return _load_backup() or default_data()

def save(data):
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)

def make_backup():
    if not DATA_FILE.exists(): return
    bp = BACKUP_DIR / f"data_{date.today()}.json"
    if not bp.exists():
        shutil.copy2(DATA_FILE, bp)
        old = sorted(BACKUP_DIR.iterdir())
        for f in old[:-30]: f.unlink()
        log.info(f"Backup: {bp.name}")

def _load_backup():
    files = sorted(BACKUP_DIR.iterdir()) if BACKUP_DIR.exists() else []
    if not files: return None
    try: return json.loads(files[-1].read_text(encoding="utf-8"))
    except: return None

def default_data():
    today = date.today().isoformat()
    return {
        "version": 2, "start_date": today,
        "end_date": "", "last_date": today,
        "streak": 1, "streak_days": [True],
        "sections": [
            {"id":"money","icon":"💰","title":"Деньги","color":"#f59e0b",
             "tasks":[{"name":"Снять 2-3 Shorts","done":False},
                      {"name":"Проанализировать просмотры","done":False},
                      {"name":"Придумать хук для следующего видео","done":False}]},
            {"id":"body","icon":"💪","title":"Тело","color":"#a78bfa",
             "tasks":[{"name":"Тренировка","done":False},
                      {"name":"Съесть 4-5 раз","done":False},
                      {"name":"Выпить 2л воды","done":False}]},
            {"id":"spirit","icon":"☪️","title":"Ахирет","color":"#34d399",
             "tasks":[{"name":"Намаз x5","done":False},
                      {"name":"Зикр утро/вечер","done":False},
                      {"name":"Сира 20 мин","done":False},
                      {"name":"Таджвид 15 мин","done":False}]},
        ],
        "stats": {"videos":0,"views":0,"subs":0,"income":0,"weight":53.0},
        "history": {"weight":[],"videos":[],"day_pct":[]},
        "notes": []
    }

def migrate(d):
    d.setdefault("version",1)
    d.setdefault("history",{"weight":[],"videos":[],"day_pct":[]})
    d["history"].setdefault("weight",[])
    d["history"].setdefault("videos",[])
    d["history"].setdefault("day_pct",[])
    d.setdefault("notes",[])
    d.setdefault("stats",{"videos":0,"views":0,"subs":0,"income":0,"weight":53.0})
    for s in d.get("sections",[]):
        s.setdefault("color","#f59e0b")
        s.setdefault("icon","📌")
        for t in s.get("tasks",[]):
            t.setdefault("done",False)
    return d

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    html_path = TMPL_DIR / "index.html"
    if not html_path.exists():
        return "<h1>templates/index.html not found</h1><p>"+str(TMPL_DIR)+"</p>", 500
    return Response(html_path.read_text(encoding="utf-8"), mimetype="text/html")

@app.route("/api/data")
def get_data():
    data  = migrate(load())
    today = date.today().isoformat()
    if data.get("last_date") != today:
        make_backup()
        all_tasks = [t for s in data["sections"] for t in s["tasks"]]
        done_cnt  = sum(1 for t in all_tasks if t["done"])
        pct       = round(done_cnt/len(all_tasks)*100) if all_tasks else 0
        data["history"]["day_pct"].append({"date":data.get("last_date",today),"pct":pct})
        data["streak_days"].append(pct==100)
        data["streak"] = (data["streak"]+1) if pct==100 else 1
        for s in data["sections"]:
            for t in s["tasks"]: t["done"] = False
        data["last_date"] = today
        save(data)
        log.info(f"New day: {today}, streak={data['streak']}, yesterday={pct}%")
    return jsonify(data)

@app.route("/api/save", methods=["POST"])
def save_route():
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict):
        return jsonify({"ok":False,"error":"invalid body"}), 400
    save(migrate(body))
    return jsonify({"ok":True})

@app.route("/api/backup", methods=["POST"])
def backup_route():
    make_backup()
    return jsonify({"ok":True})

@app.route("/health")
def health():
    return jsonify({"status":"ok","time":datetime.now().isoformat()})

@app.errorhandler(404)
def not_found(e): return jsonify({"error":"not found"}), 404

@app.errorhandler(500)
def err500(e): log.error(e); return jsonify({"error":str(e)}), 500

# ── Start ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    log.info(f"Starting on port {port}")
    log.info(f"BASE_DIR: {BASE_DIR}")
    log.info(f"TMPL_DIR exists: {TMPL_DIR.exists()}")
    log.info(f"index.html exists: {(TMPL_DIR/'index.html').exists()}")
    make_backup()
    try:
        from waitress import serve
        log.info("Using waitress")
        serve(app, host="0.0.0.0", port=port, threads=4)
    except ImportError:
        log.info("Using Flask dev server")
        app.run(host="0.0.0.0", port=port, debug=False)
