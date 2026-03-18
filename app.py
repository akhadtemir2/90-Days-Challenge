"""
Growth OS — Production Server
"""

from flask import Flask, render_template, request, jsonify
import json, os, webbrowser, threading, shutil, logging
from datetime import datetime, date

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("growth_os.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.config["JSON_ENSURE_ASCII"] = False

DATA_FILE   = "data.json"
BACKUP_DIR  = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# ── Data helpers ─────────────────────────────────────────────────────────────

def load() -> dict:
    if not os.path.exists(DATA_FILE):
        d = default_data()
        save(d)
        return d
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Ошибка загрузки data.json: {e}")
        # Пробуем последний бэкап
        return _load_latest_backup() or default_data()


def save(data: dict) -> None:
    try:
        # Атомарная запись через временный файл
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)
    except Exception as e:
        log.error(f"Ошибка сохранения: {e}")
        raise


def make_backup() -> str | None:
    """Создаёт бэкап раз в день"""
    if not os.path.exists(DATA_FILE):
        return None
    today = date.today().strftime("%Y-%m-%d")
    backup_path = os.path.join(BACKUP_DIR, f"data_{today}.json")
    if not os.path.exists(backup_path):
        shutil.copy2(DATA_FILE, backup_path)
        # Оставляем только последние 30 бэкапов
        backups = sorted(os.listdir(BACKUP_DIR))
        for old in backups[:-30]:
            os.remove(os.path.join(BACKUP_DIR, old))
        log.info(f"Бэкап создан: {backup_path}")
        return backup_path
    return None


def _load_latest_backup() -> dict | None:
    backups = sorted(os.listdir(BACKUP_DIR))
    if not backups:
        return None
    latest = os.path.join(BACKUP_DIR, backups[-1])
    try:
        with open(latest, encoding="utf-8") as f:
            log.warning(f"Восстановление из бэкапа: {latest}")
            return json.load(f)
    except Exception:
        return None


def default_data() -> dict:
    today = date.today().strftime("%Y-%m-%d")
    return {
        "version":    2,
        "start_date": "2026-03-18",
        "end_date":   "2026-06-16",
        "last_date":  today,
        "streak":     1,
        "streak_days": [True],
        "sections": [
            {
                "id": "money", "icon": "💰",
                "title": "Деньги", "color": "#f59e0b",
                "tasks": [
                    {"name": "Снять 2-3 Shorts",                   "done": False},
                    {"name": "Проанализировать просмотры",           "done": False},
                    {"name": "Придумать хук для следующего видео",   "done": False},
                ]
            },
            {
                "id": "body", "icon": "💪",
                "title": "Тело", "color": "#a78bfa",
                "tasks": [
                    {"name": "Тренировка",   "done": False},
                    {"name": "Съесть 4-5 раз","done": False},
                    {"name": "Выпить 2л воды","done": False},
                ]
            },
            {
                "id": "spirit", "icon": "☪️",
                "title": "Ахирет", "color": "#34d399",
                "tasks": [
                    {"name": "Намаз x5",        "done": False},
                    {"name": "Зикр утро/вечер", "done": False},
                    {"name": "Сира 20 мин",     "done": False},
                    {"name": "Таджвид 15 мин",  "done": False},
                ]
            }
        ],
        "stats": {
            "videos": 0, "views": 0, "subs": 0, "income": 0, "weight": 53.0
        },
        "history": {
            "weight":  [],   # [{date, value}]
            "videos":  [],   # [{date, count}]
            "day_pct": [],   # [{date, pct}]
        },
        "notes": []
    }


def migrate(data: dict) -> dict:
    """Автоматически добавляет новые поля без потери старых данных"""
    data.setdefault("version", 1)
    data.setdefault("history", {"weight": [], "videos": [], "day_pct": []})
    data["history"].setdefault("weight",  [])
    data["history"].setdefault("videos",  [])
    data["history"].setdefault("day_pct", [])
    data.setdefault("notes", [])
    data.setdefault("stats", {"videos":0,"views":0,"subs":0,"income":0,"weight":53.0})
    for s in data.get("sections", []):
        s.setdefault("color", "#f59e0b")
        s.setdefault("icon",  "📌")
        for t in s.get("tasks", []):
            t.setdefault("done", False)
            t.setdefault("created", date.today().strftime("%Y-%m-%d"))
    return data


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def get_data():
    data = migrate(load())
    today = date.today().strftime("%Y-%m-%d")

    if data.get("last_date") != today:
        make_backup()

        # Считаем % выполнения вчера
        all_tasks = [t for s in data["sections"] for t in s["tasks"]]
        done_cnt  = sum(1 for t in all_tasks if t["done"])
        pct       = round(done_cnt / len(all_tasks) * 100) if all_tasks else 0

        # Сохраняем в историю
        yesterday = data.get("last_date", today)
        data["history"]["day_pct"].append({"date": yesterday, "pct": pct})

        # Streak
        all_done = pct == 100
        data["streak_days"].append(all_done)
        data["streak"] = (data["streak"] + 1) if all_done else 1

        # Сброс задач
        for s in data["sections"]:
            for t in s["tasks"]:
                t["done"] = False

        data["last_date"] = today
        save(data)
        log.info(f"Новый день: {today}, streak={data['streak']}, вчера={pct}%")

    return jsonify(data)


@app.route("/api/save", methods=["POST"])
def save_route():
    body = request.get_json(force=True)
    if not body or not isinstance(body, dict):
        return jsonify({"ok": False, "error": "invalid body"}), 400
    save(migrate(body))
    return jsonify({"ok": True})


@app.route("/api/backup", methods=["POST"])
def backup_route():
    path = make_backup()
    return jsonify({"ok": True, "path": path})


@app.route("/api/backups")
def list_backups():
    files = sorted(os.listdir(BACKUP_DIR), reverse=True)[:10]
    return jsonify({"backups": files})


@app.route("/api/history")
def get_history():
    data = load()
    return jsonify(data.get("history", {}))


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(500)
def server_error(e):
    log.error(f"500 error: {e}")
    return jsonify({"error": "server error"}), 500


# ── Run ──────────────────────────────────────────────────────────────────────

def open_browser():
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    log.info("Growth OS запускается...")
    make_backup()

    print("\n" + "=" * 50)
    print("  Growth OS v2  —  Production Ready")
    print("  http://localhost:5000")
    print("  Логи: growth_os.log")
    print("  Бэкапы: ./backups/")
    print("=" * 50 + "\n")

    threading.Timer(1.2, open_browser).start()

    try:
        # Пробуем production-сервер waitress
        from waitress import serve
        log.info("Запуск через waitress (production)")
        serve(app, host="0.0.0.0", port=5000, threads=4)
    except ImportError:
        # Fallback на встроенный Flask
        log.info("waitress не установлен, запуск через Flask dev server")
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
