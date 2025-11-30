import psutil
import platform
import time
from datetime import timedelta
from flask import Flask, render_template_string

app = Flask(__name__)
start_time = time.time()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <title>AJNA Dashboard</title>
    <style>
        body { background: #121212; color: #fff; font-family: sans-serif; text-align: center; padding: 50px; }
        h1 { color: #00ff88; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 10px; display: inline-block; margin: 10px; width: 200px; }
        .val { font-size: 2em; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🎛️ AJNA SYSTEM STATUS</h1>
    <div class="card"><div>CPU</div><div class="val">{{ cpu }}%</div></div>
    <div class="card"><div>RAM</div><div class="val">{{ ram }}%</div></div>
    <div class="card"><div>UPTIME</div><div>{{ uptime }}</div></div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE, 
        cpu=psutil.cpu_percent(),
        ram=psutil.virtual_memory().percent,
        uptime=str(timedelta(seconds=int(time.time() - start_time)))
    )

if __name__ == '__main__':
    print("🚀 Serwer startuje na porcie 5000...")
    app.run(host='0.0.0.0', port=5000)
