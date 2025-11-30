from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
import redis
import json
import qrcode
from io import BytesIO

app = Flask(__name__)
CORS(app)

REDIS_URL = os.getenv('REDIS_URL', 'redis://db-redis:6379')

SERVICE_TYPE = os.getenv('SERVICE_TYPE', 'generico')

try:
    db = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    print(f"✅ Conectado a Redis: {REDIS_URL.split('@')[-1]}") 
except Exception as e:
    db = None
    print(f"❌ Error Redis: {e}")

def is_service(target):
    return SERVICE_TYPE == 'all' or SERVICE_TYPE == target

@app.route('/')
def salud(): return f"Servicio Activo: {SERVICE_TYPE}"

# --- USUARIOS ---
@app.route('/register', methods=['POST'])
def register_user():
    if not is_service('users'): return jsonify({"error": "Wrong service"})
    
    data = request.json
    email = data.get('email')
    if db:
        if not db.exists(f"user:{email}"): db.set(f"user:{email}", json.dumps(data))
        return jsonify({"status": "ok", "user": json.loads(db.get(f"user:{email}"))})
    return jsonify({"error": "No DB"}), 500

@app.route('/user/<email>', methods=['GET'])
def get_user(email):
    if not is_service('users'): return jsonify({"error": "Wrong service"})
    
    if db and db.exists(f"user:{email}"): return jsonify(json.loads(db.get(f"user:{email}")))
    return jsonify({"error": "User not found"}), 404

# --- LINKS ---
@app.route('/links/<email>', methods=['GET'])
def get_links(email):
    if not is_service('links'): return jsonify({"error": "Wrong service"})
    
    if db:
        raw_links = db.get(f"links:{email}")
        links = json.loads(raw_links) if raw_links else []
        
        active_links = []
        for link in links:
            if 'max_clicks' in link and link['max_clicks']:
                remaining = db.get(f"snap:{link['id']}")
                if not remaining or int(remaining) <= 0:
                    continue
            active_links.append(link)
        return jsonify(active_links)
    return jsonify([])

@app.route('/links/stats/<email>', methods=['GET'])
def get_link_stats(email):
    if not is_service('links'): return jsonify({"error": "Wrong service"})
    
    if db:
        raw_links = db.get(f"links:{email}")
        links = json.loads(raw_links) if raw_links else []
        stats = []
        for link in links:
            total = db.get(f"clicks:link:{link['id']}")
            remaining = db.get(f"snap:{link['id']}")
            stats.append({
                "id": link['id'],
                "title": link['title'],
                "url": link['url'],
                "clicks": int(total) if total else 0,
                "is_snap": True if 'max_clicks' in link and link['max_clicks'] else False,
                "remaining": int(remaining) if remaining else None
            })
        return jsonify(stats)
    return []

@app.route('/links/add', methods=['POST'])
def add_link():
    if not is_service('links'): return jsonify({"error": "Wrong service"})
    
    data = request.json
    email = data.get('email')
    max_clicks = data.get('max_clicks')
    new_link = {
        "id": data.get('id'),
        "title": data.get('title'),
        "url": data.get('url'),
        "tag": data.get('tag', 'general'),
        "max_clicks": max_clicks
    }
    
    if db:
        if max_clicks: db.set(f"snap:{new_link['id']}", int(max_clicks))
        
        raw_links = db.get(f"links:{email}")
        links = json.loads(raw_links) if raw_links else []
        links.append(new_link)
        db.set(f"links:{email}", json.dumps(links))
        return jsonify({"status": "added", "links": links})
    return jsonify({"error": "No DB"})

@app.route('/qr/<email>', methods=['GET'])
def generate_qr(email):
    if not is_service('links'): return jsonify({"error": "Wrong service"})
    
    try:
        FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost')
        profile_url = f"{FRONTEND_URL}/?user={email}"
        
        img = qrcode.make(profile_url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ANALYTICS ---
@app.route('/track', methods=['POST'])
def track_click():
    if not is_service('analytics'): return jsonify({"error": "Wrong service"})
    
    data = request.json
    link_id = data.get('link_id')
    if db:
        new = db.incr(f"clicks:link:{link_id}")
        if db.exists(f"snap:{link_id}"): db.decr(f"snap:{link_id}")
        return jsonify({"status": "ok", "total": new})
    return jsonify({"status": "error_db"})

# --- NOTIFICACIONES ---
@app.route('/notify', methods=['POST'])
def notify():
    if not is_service('notifications'): return jsonify({"error": "Wrong service"})
    print(f"🔔 Notificación Cloud: {request.json}")
    return jsonify({"status": "sent"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)