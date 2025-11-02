import sys
import subprocess
import uuid
import random
from flask import Flask, request, redirect, url_for, render_template_string, abort, jsonify

# --- CONFIG ---
KOFI_URL = "https://ko-fi.com/toccaate"
REQUIRED_PACKAGES = ["flask"]

def ensure_packages(packages):
    missing = []
    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if not missing:
        return
    print(f"[setup] Mancano: {', '.join(missing)}")
    try:
        import sys, subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
    except Exception as e:
        print("[setup] installazione fallita:", e)
        sys.exit(1)

ensure_packages(REQUIRED_PACKAGES)

app = Flask(__name__)

# id -> {title, options, picked, history}
CHOICES = {}

BASE_HTML = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body { background:#f5f5f7; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin:0; }
    .wrap { max-width: 520px; margin: 40px auto; background:#fff; border-radius: 20px; padding: 28px; box-shadow: 0 18px 50px rgba(0,0,0,.04); }
    h1 { font-size: 1.5rem; margin-bottom: .4rem; }
    p { color:#555; }
    input[type=text] { width:100%; padding:10px 12px; border:1px solid #e5e5e5; border-radius:14px; margin-bottom:10px; font-size:.95rem; }
    button, .btn { background:#4a6cf7; color:white; border:none; padding:11px 16px; border-radius:14px; font-weight:600; cursor:pointer; font-size:.95rem; text-decoration:none; display:inline-block; }
    button.secondary, .btn.secondary { background:#edf0ff; color:#20308f; }
    .options { margin-top: 10px; }
    .result { font-size: 1.6rem; font-weight: 700; text-align:center; margin:25px 0; }
    .badge { display:inline-block; background:#ffeaa7; padding:3px 10px; border-radius:999px; font-size:.7rem; margin-bottom:10px; }
    .small { font-size:.8rem; color:#777; }
    .center { text-align:center; }
    input.readonly-like {
        width:100%;
        padding:10px 12px;
        border:1px solid #e5e5e5;
        border-radius:14px;
        margin-bottom:10px;
        font-size:.85rem;
        background:#fff;
    }
    .history-item { background:#f5f5f7; margin-bottom:6px; padding:6px 10px; border-radius:10px; }
  </style>
</head>
<body>
  <div class="wrap">
    {{ content|safe }}
    <p class="center" style="margin-top:18px;">
      <a class="small" href=\"""" + KOFI_URL + """\" target="_blank">☕ Supporta ToccaATE su Ko-fi</a>
    </p>
  </div>
</body>
</html>
"""

def render_page(title: str, inner_html: str):
    return render_template_string(BASE_HTML, title=title, content=inner_html)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        opts = [
            request.form.get("opt1", "").strip(),
            request.form.get("opt2", "").strip(),
            request.form.get("opt3", "").strip(),
            request.form.get("opt4", "").strip(),
        ]
        opts = [o for o in opts if o]
        if len(opts) < 2:
            return render_page("ToccaATE - Errore", """
            <h1>ToccaATE 😅</h1>
            <p>Devi darmi almeno 2 opzioni.</p>
            <p><a class="btn secondary" href="/">Torna indietro</a></p>
            """)
        choice_id = str(uuid.uuid4())
        CHOICES[choice_id] = {
            "title": request.form.get("title", "").strip() or "ToccaATE",
            "options": opts,
            "picked": None,
            "history": []
        }
        return redirect(url_for("share", choice_id=choice_id))

    return render_page("ToccaATE", """
    <span class="badge">ToccaATE 🎯</span>
    <h1>Non vuoi scegliere?</h1>
    <p>Scrivi 2 o più opzioni. Tocca a me.</p>
    <form method="post">
      <input name="title" type="text" placeholder="Titolo (es. cosa mangio?)">
      <div class="options">
        <input name="opt1" type="text" placeholder="Opzione 1" required>
        <input name="opt2" type="text" placeholder="Opzione 2" required>
        <input name="opt3" type="text" placeholder="Opzione 3 (opzionale)">
        <input name="opt4" type="text" placeholder="Opzione 4 (opzionale)">
      </div>
      <button type="submit">ToccaATE!</button>
    </form>
    """)

@app.route("/share/<choice_id>")
def share(choice_id):
    data = CHOICES.get(choice_id)
    if not data:
        abort(404)
    share_link = request.host_url.strip("/") + url_for("decide_for_friend", choice_id=choice_id)
    wait_link = url_for("wait_for_choice", choice_id=choice_id)
    result_link = url_for("result", choice_id=choice_id)
    return render_page("ToccaATE - Condividi", f"""
    <span class="badge">Condividi</span>
    <h1>Invia il link</h1>
    <p>Manda questo link a chi deve scegliere per te:</p>
    <input class="readonly-like" type="text" value="{share_link}" onclick="this.select()" readonly>
    <p class="small">Tieni aperta la pagina di attesa per vedere tutte le scelte:</p>
    <p class="center" style="margin-top:12px;">
      <a class="btn" href="{wait_link}">Apri pagina di attesa</a>
    </p>
    <p class="center" style="margin-top:8px;">
      <a class="small" href="{result_link}">Vedi ultima scelta</a>
    </p>
    <p class="center" style="margin-top:8px;">
      <a class="small" href="/">Nuova scelta</a>
    </p>
    """)

@app.route("/wait/<choice_id>")
def wait_for_choice(choice_id):
    data = CHOICES.get(choice_id)
    if not data:
        abort(404)
    status_url = url_for("status", choice_id=choice_id)
    result_url = url_for("result", choice_id=choice_id)
    return render_page("ToccaATE - In attesa", f"""
    <span class="badge">Attesa</span>
    <h1>{data['title']}</h1>
    <p>Sto aspettando che i tuoi amici scelgano… lascia aperta questa pagina.</p>
    <div id="last-choice" style="margin-top:12px;"></div>
    <p class="center" style="margin-top:12px;">
      <a class="btn secondary" href="{result_url}">Apri risultato</a>
    </p>
    <script>
      let lastCount = 0;
      async function poll() {{
        try {{
          const res = await fetch("{status_url}");
          const data = await res.json();
          if (data.count > lastCount) {{
            lastCount = data.count;
            document.getElementById("last-choice").innerText = "Nuova scelta: " + data.picked;
            alert("Nuova scelta: " + data.picked);
          }}
        }} catch (e) {{}}
        setTimeout(poll, 2000);
      }}
      poll();
    </script>
    """)

@app.route("/status/<choice_id>")
def status(choice_id):
    data = CHOICES.get(choice_id)
    if not data:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "picked": data["picked"],
        "title": data["title"],
        "options": data["options"],
        "count": len(data["history"]),
    })

@app.route("/r/<choice_id>")
def result(choice_id):
    data = CHOICES.get(choice_id)
    if not data:
        abort(404)
    if data["picked"] is None:
        first = random.choice(data["options"])
        data["picked"] = first
        data["history"].append(first)

    index_url = url_for("index")
    share_link = request.host_url.strip("/") + url_for("decide_for_friend", choice_id=choice_id)

    history_html = ""
    for i, item in enumerate(data["history"], start=1):
        history_html += f'<div class="history-item">#{i}: {item}</div>'

    return render_page("ToccaATE - Risultato", f"""
    <span class="badge">La scelta di ToccaATE</span>
    <h1>{data['title']}</h1>
    <div class="result">{data['picked']}</div>
    <p class="small">Opzioni possibili: {", ".join(data["options"])}</p>
    <p class="small">Link per far scegliere ancora:</p>
    <input class="readonly-like" type="text" value="{share_link}" onclick="this.select()" readonly>
    <h2 style="margin-top:20px;font-size:1rem;">Scelte ricevute</h2>
    {history_html or "<p class='small'>Nessuna scelta registrata.</p>"}
    <p class="center" style="margin-top:16px;"><a class="btn secondary" href="{index_url}">Nuova scelta</a></p>
    """)

@app.route("/decidi/<choice_id>", methods=["GET", "POST"])
def decide_for_friend(choice_id):
    data = CHOICES.get(choice_id)
    if not data:
        abort(404)

    if request.method == "POST":
        picked = request.form.get("picked")
        if picked in data["options"]:
            data["picked"] = picked
            data["history"].append(picked)
            return redirect(url_for("result", choice_id=choice_id))

    buttons_html = "".join(
        f'<button name="picked" value="{opt}" style="display:block;width:100%;margin-bottom:8px;">{opt}</button>'
        for opt in data["options"]
    )

    return render_page("ToccaATE - Decidi", f"""
    <span class="badge">Tocca a TE 😎</span>
    <h1>{data['title']}</h1>
    <p>Scegli tu per l'altra persona:</p>
    <form method="post">
      {buttons_html}
    </form>
    """)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
