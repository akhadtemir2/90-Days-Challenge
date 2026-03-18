"""
Growth OS — Полная рабочая версия (с удалением, редактированием и сохранением)
"""
from flask import Flask, jsonify, request, Response
import json, os, shutil, logging, pathlib
from datetime import datetime, date

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BASE_DIR   = pathlib.Path(__file__).parent.resolve()
DATA_FILE  = BASE_DIR / "data.json"
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["JSON_ENSURE_ASCII"] = False

# ── ОЖИВЛЕННЫЙ ИНТЕРФЕЙС ──────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Growth OS</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        *{box-sizing:border-box;margin:0;padding:0;font-family:'Inter',sans-serif}
        body{background:#070707;color:#fff;padding:20px}
        .container{max-width:500px;margin:0 auto}
        .header{text-align:center;margin-bottom:30px}
        .timer{font-size:24px;font-weight:800;color:#f59e0b;margin:10px 0}
        .progress-circle{width:80px;height:80px;border-radius:50%;border:4px solid #222;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;font-weight:800;font-size:18px;border-top-color:#22c55e}
        
        .section{background:#111;border-radius:15px;padding:15px;margin-bottom:20px;border:1px solid #222}
        .section-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}
        .section-title{display:flex;align-items:center;gap:10px;cursor:pointer}
        .section-title:hover{opacity:0.8}
        
        .task-item{display:flex;justify-content:space-between;align-items:center;background:#181818;padding:12px;border-radius:10px;margin-bottom:8px;transition:0.2s}
        .task-left{display:flex;align-items:center;gap:12px;flex:1}
        .task-name{font-size:14px;cursor:pointer}
        .task-name.done{text-decoration:line-through;opacity:0.4}
        
        input[type="checkbox"]{width:20px;height:20px;accent-color:#22c55e;cursor:pointer}
        
        .btn-add{background:#222;border:none;color:#888;padding:8px 15px;border-radius:8px;cursor:pointer;font-size:12px}
        .btn-add:hover{background:#333;color:#fff}
        .btn-del{background:none;border:none;color:#444;cursor:pointer;padding:5px;font-size:16px}
        .btn-del:hover{color:#ef4444}
        
        .footer-nav{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);display:flex;gap:20px;background:rgba(0,0,0,0.8);padding:10px 20px;border-radius:30px;backdrop-filter:blur(10px);border:1px solid #333}
        .nav-item{color:#666;text-decoration:none;font-size:20px}
        .nav-item.active{color:#fff}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="progress-circle" id="dayProgress">0%</div>
            <h1>Growth OS</h1>
            <div class="timer" id="countdown">Загрузка...</div>
        </div>

        <div id="sectionsList"></div>
    </div>

    <script>
        let appData = {};

        async function loadData() {
            const res = await fetch('/api/data');
            appData = await res.json();
            renderAll();
        }

        async function saveAll() {
            await fetch('/api/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(appData)
            });
            renderAll();
        }

        function renderAll() {
            // Таймер
            const end = new Date(appData.end_date);
            const now = new Date();
            const diff = end - now;
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            document.getElementById('countdown').innerText = days + " ДНЕЙ ОСТАЛОСЬ";

            // Секции
            const list = document.getElementById('sectionsList');
            list.innerHTML = '';
            
            let totalTasks = 0;
            let doneTasks = 0;

            appData.sections.forEach(sec => {
                let tasksHtml = '';
                sec.tasks.forEach((task, idx) => {
                    totalTasks++;
                    if(task.done) doneTasks++;
                    tasksHtml += `
                        <div class="task-item">
                            <div class="task-left">
                                <input type="checkbox" ${task.done ? 'checked' : ''} onchange="toggleTask('${sec.id}', ${idx})">
                                <span class="task-name ${task.done ? 'done' : ''}">${task.name}</span>
                            </div>
                            <button class="btn-del" onclick="deleteTask('${sec.id}', ${idx})">🗑️</button>
                        </div>
                    `;
                });

                list.innerHTML += `
                    <div class="section" style="border-top: 3px solid ${sec.color}">
                        <div class="section-header">
                            <div class="section-title" onclick="editSection('${sec.id}')">
                                <span>${sec.icon}</span>
                                <strong>${sec.title}</strong>
                            </div>
                            <button class="btn-add" onclick="addTask('${sec.id}')">+ Добавить</button>
                        </div>
                        <div class="tasks">${tasksHtml}</div>
                    </div>
                `;
            });

            const pct = totalTasks > 0 ? Math.round((doneTasks/totalTasks)*100) : 0;
            document.getElementById('dayProgress').innerText = pct + '%';
        }

        function toggleTask(secId, idx) {
            const sec = appData.sections.find(s => s.id === secId);
            sec.tasks[idx].done = !sec.tasks[idx].done;
            saveAll();
        }

        function addTask(secId) {
            const name = prompt("Что нужно сделать?");
            if(name) {
                const sec = appData.sections.find(s => s.id === secId);
                sec.tasks.push({name: name, done: false});
                saveAll();
            }
        }

        function deleteTask(secId, idx) {
            if(confirm("Удалить задачу?")) {
                const sec = appData.sections.find(s => s.id === secId);
                sec.tasks.splice(idx, 1);
                saveAll();
            }
        }

        function editSection(secId) {
            const sec = appData.sections.find(s => s.id === secId);
            const newTitle = prompt("Новое название приоритета:", sec.title);
            if(newTitle) {
                sec.title = newTitle;
                saveAll();
            }
        }

        loadData();
        setInterval(renderAll, 60000); // Обновлять таймер раз в минуту
    </script>
</body>
</html>
"""

# ── BACKEND LOGIC ─────────────────────────────────────────────────────────────

def _load():
    if not DATA_FILE.exists():
        # Начальные данные, если файла нет
        default = {
            "end_date": "2026-06-16",
            "last_date": str(date.today()),
            "sections": [
                {"id":"money", "title":"Деньги", "icon":"💰", "color":"#f59e0b", "tasks":[]},
                {"id":"body", "title":"Тело", "icon":"💪", "color":"#8b5cf6", "tasks":[]},
                {"id":"spirit", "title":"Духовность", "icon":"☪️", "color":"#22c55e", "tasks":[]}
            ]
        }
        _save(default)
        return default
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))

def _save(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")

@app.route("/api/data")
def get_data():
    return jsonify(_load())

@app.route("/api/save", methods=["POST"])
def save_data():
    data = request.json
    _save(data)
    return jsonify({"ok": True})

@app.route("/health")
def health(): return "ok"

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0
