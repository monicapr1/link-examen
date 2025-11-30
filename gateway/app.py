from flask import Flask, jsonify, redirect, request, Response
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- CONFIGURACIÓN HÍBRIDA ---
CLOUD_URL = os.getenv('BACKEND_URL')

if CLOUD_URL:
    print(f"☁️ Modo Nube Activado. Backend en: {CLOUD_URL}")
    URLS = {
        "users": CLOUD_URL,
        "links": CLOUD_URL,
        "analytics": CLOUD_URL,
        "notif": CLOUD_URL
    }
else:
    print("🏠 Modo Local (Docker).")
    URLS = {
        "users": "http://ms-users:5000",
        "links": "http://ms-links:5000",
        "analytics": "http://ms-analytics:5000",
        "notif": "http://ms-notifications:5000"
    }

def safe_req(method, url, json_data=None, default=None):
    try:
        if method == 'GET': return requests.get(url, timeout=3).json() #
        elif method == 'POST': return requests.post(url, json=json_data, timeout=3).json()
    except Exception as e:
        print(f"Error conectando a {url}: {e}")
        return default

# --- RUTAS ---

@app.route('/api/login', methods=['POST'])
def login():
    return jsonify(safe_req('POST', f"{URLS['users']}/register", request.json, {"error": "Service Down"}))

@app.route('/api/profile/<email>')
def get_profile(email):
    user = safe_req('GET', f"{URLS['users']}/user/{email}", None, {"name": "Anonimo"})
    links = safe_req('GET', f"{URLS['links']}/links/{email}", None, [])
    try: requests.post(f"{URLS['notif']}/notify", json={"event": f"view_profile_{email}"}, timeout=0.1)
    except: pass
    return jsonify({"user": user, "links": links})

@app.route('/api/dashboard/<email>')
def get_dashboard_stats(email):
    return jsonify(safe_req('GET', f"{URLS['links']}/links/stats/{email}", None, []))

@app.route('/api/links/add', methods=['POST'])
def add_link():
    return jsonify(safe_req('POST', f"{URLS['links']}/links/add", request.json, {"error": "Service Down"}))

@app.route('/api/qr/<email>')
def get_qr(email):
    try:
        resp = requests.get(f"{URLS['links']}/qr/{email}", stream=True, timeout=3)
        return Response(resp.content, mimetype='image/png')
    except:
        return "QR Error", 404

@app.route('/api/click')
def click():
    url = request.args.get('url')
    link_id = request.args.get('id')
    try:
        requests.post(f"{URLS['analytics']}/track", json={"link_id": link_id}, timeout=0.5)
    except:
        print("Analytics caído")
    
    if not url: return redirect("/", code=302)
    return redirect(url, code=302)

@app.route('/')
def home():
    return "Gateway Activo 🚀"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)