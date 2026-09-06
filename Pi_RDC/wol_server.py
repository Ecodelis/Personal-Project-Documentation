import os
import subprocess
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
SECRET = os.environ.get("WAKE_SECRET")
MAC = os.environ.get("WAKE_MAC")
PC_TAILSCALE_IP = os.environ.get("PC_TAILSCALE_IP")
RECHECK_SECONDS = 10

def is_pc_reachable():
    result = subprocess.run(
        ['ping', '-c', '1', '-W', '1', PC_TAILSCALE_IP],
        capture_output=True
    )
    return result.returncode == 0

PAGE = """
<!DOCTYPE html>
<html>
<head>
  <title>Wake PC</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, 'Segoe UI', Roboto, sans-serif;
      background: #0d0f12;
      color: #e8e8e8;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .card {
      background: #17191d;
      border: 1px solid #2a2d33;
      border-radius: 16px;
      padding: 40px 32px;
      width: 100%;
      max-width: 340px;
      text-align: center;
    }
    h1 {
      font-size: 18px;
      font-weight: 500;
      color: #f0f0f0;
      margin-bottom: 6px;
    }
    .subtitle {
      font-size: 13px;
      color: #7a7d85;
      margin-bottom: 6px;
    }
    .recheck {
      font-size: 11px;
      color: #4a4d54;
      margin-bottom: 26px;
    }
    button {
      width: 100%;
      padding: 16px;
      font-size: 16px;
      font-weight: 500;
      border-radius: 12px;
      border: none;
      background: #3b6ef6;
      color: white;
      cursor: pointer;
      transition: background 0.15s, transform 0.1s;
    }
    button:hover { background: #2f5bd6; }
    button:active { transform: scale(0.97); }
    button:disabled { background: #2a2d33; color: #6a6d75; cursor: default; }
    #status {
      margin-top: 20px;
      font-size: 13px;
      color: #7a7d85;
      min-height: 18px;
    }
    #status.ok { color: #4ade80; }
    #status.err { color: #f87171; }
    .dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #4a4d54;
      margin-right: 6px;
      vertical-align: middle;
      transition: background 0.3s;
    }
    .dot.connected { background: #4ade80; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Wake PC</h1>
    <p class="subtitle"><span class="dot" id="dot"></span><span id="conn-text">Checking...</span></p>
    <p class="recheck" id="recheck">Rechecking in RECHECK_SECONDS_PLACEHOLDERs</p>
    <button id="btn" onclick="wake()">Send wake signal</button>
    <div id="status"></div>
  </div>
  <script>
    const RECHECK_SECONDS = RECHECK_SECONDS_PLACEHOLDER;
    let countdown = RECHECK_SECONDS;

    async function checkStatus() {
      try {
        const res = await fetch('/status');
        const data = await res.json();
        const dot = document.getElementById('dot');
        const connText = document.getElementById('conn-text');
        if (data.reachable) {
          dot.classList.add('connected');
          connText.textContent = 'Connected';
        } else {
          dot.classList.remove('connected');
          connText.textContent = 'Disconnected';
        }
      } catch (e) {
        document.getElementById('dot').classList.remove('connected');
        document.getElementById('conn-text').textContent = 'Disconnected';
      }
      countdown = RECHECK_SECONDS;
    }

    function tickCountdown() {
      const recheckEl = document.getElementById('recheck');
      recheckEl.textContent = 'Rechecking in ' + countdown + 's';
      countdown--;
      if (countdown < 0) {
        checkStatus();
      }
    }

    checkStatus();
    setInterval(tickCountdown, 1000);

    async function wake() {
      const btn = document.getElementById('btn');
      const status = document.getElementById('status');
      btn.disabled = true;
      btn.textContent = 'Sending...';
      status.className = '';
      status.textContent = '';
      try {
        const res = await fetch('/wake?key=SECRET_PLACEHOLDER', { method: 'POST' });
        const text = await res.text();
        status.textContent = text;
        status.className = res.ok ? 'ok' : 'err';
      } catch (e) {
        status.textContent = 'Request failed';
        status.className = 'err';
      }
      btn.disabled = false;
      btn.textContent = 'Send wake signal';
    }
  </script>
</body>
</html>
""".replace("SECRET_PLACEHOLDER", SECRET or "").replace("RECHECK_SECONDS_PLACEHOLDER", str(RECHECK_SECONDS))

@app.route('/')
def index():
    return PAGE

@app.route('/status')
def status():
    return jsonify(reachable=is_pc_reachable())

@app.route('/wake', methods=['POST'])
def wake():
    if request.args.get('key') != SECRET:
        return "Forbidden", 403
    subprocess.run(['wakeonlan', MAC])
    return "Magic packet sent"

if __name__ == '__main__':
    if not SECRET or not MAC or not PC_TAILSCALE_IP:
        raise RuntimeError("Missing WAKE_SECRET, WAKE_MAC, or PC_TAILSCALE_IP in .env")
    app.run(host='0.0.0.0', port=5000)