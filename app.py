from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import psycopg2
import psycopg2.extras
import qrcode
import io
import base64
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kaleidoscop-secret-2024')
@app.route('/')
def index():
    return redirect(url_for('admin_login'))

# ─── DB CONFIG ────────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'kaleidoscop'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'password'),
    'port': os.environ.get('DB_PORT', 5432),
}

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin2024')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            country VARCHAR(100),
            emoji VARCHAR(10),
            color VARCHAR(20) DEFAULT '#FF8C00',
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS participants (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(100) UNIQUE NOT NULL,
            team_id INTEGER REFERENCES teams(id),
            joined_at TIMESTAMP DEFAULT NOW(),
            voted_for INTEGER REFERENCES teams(id)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# ─── ADMIN ROUTES ─────────────────────────────────────────────────────────────

@app.route('/admin')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin/auth', methods=['POST'])
def admin_auth():
    pwd = request.form.get('password')
    if pwd == ADMIN_PASSWORD:
        session['is_admin'] = True
        return redirect(url_for('admin_qr'))
    return render_template('admin_login.html', error='Неверный пароль')

@app.route('/admin/qr')
def admin_qr():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    user_url = f"{BASE_URL}/join"
    img = qrcode.make(user_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template('admin_qr.html', qr_code=qr_b64, user_url=user_url)

@app.route('/admin/rating')
def admin_rating():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    return render_template('admin_rating.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

# ─── USER ROUTES ──────────────────────────────────────────────────────────────

@app.route('/join')
def user_join():
    if 'user_session' not in session:
        import uuid
        session['user_session'] = str(uuid.uuid4())
        # Register participant
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO participants (session_id) VALUES (%s) ON CONFLICT DO NOTHING",
                        (session['user_session'],))
            conn.commit()
        except:
            conn.rollback()
        cur.close()
        conn.close()
    return render_template('user_choose_team.html')

@app.route('/vote')
def user_vote():
    if 'user_session' not in session:
        return redirect(url_for('user_join'))
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT team_id FROM participants WHERE session_id=%s", (session['user_session'],))
    p = cur.fetchone()
    cur.close()
    conn.close()
    if not p or not p['team_id']:
        return redirect(url_for('user_join'))
    return render_template('user_vote.html')

# ─── API ──────────────────────────────────────────────────────────────────────

@app.route('/api/teams')
def api_teams():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT t.*, 
               COUNT(DISTINCT p.id) as members,
               COUNT(DISTINCT p2.id) as votes
        FROM teams t
        LEFT JOIN participants p ON p.team_id = t.id
        LEFT JOIN participants p2 ON p2.voted_for = t.id
        GROUP BY t.id
        ORDER BY votes DESC, members DESC
    """)
    teams = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(t) for t in teams])

@app.route('/api/stats')
def api_stats():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) as total FROM participants")
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as voted FROM participants WHERE voted_for IS NOT NULL")
    voted = cur.fetchone()['voted']
    cur.execute("SELECT COUNT(*) as teams FROM teams")
    teams = cur.fetchone()['teams']
    cur.close()
    conn.close()
    return jsonify({'online': total, 'voted': voted, 'teams': teams})

@app.route('/api/teams', methods=['POST'])
def api_create_team():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO teams (name, country, emoji, color) VALUES (%s,%s,%s,%s) RETURNING *",
        (data['name'], data.get('country',''), data.get('emoji','🌍'), data.get('color','#FF8C00'))
    )
    team = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(dict(team))

@app.route('/api/teams/<int:team_id>', methods=['DELETE'])
def api_delete_team(team_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE participants SET team_id=NULL WHERE team_id=%s", (team_id,))
    cur.execute("UPDATE participants SET voted_for=NULL WHERE voted_for=%s", (team_id,))
    cur.execute("DELETE FROM teams WHERE id=%s", (team_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/join-team', methods=['POST'])
def api_join_team():
    if 'user_session' not in session:
        return jsonify({'error': 'No session'}), 400
    data = request.json
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT team_id FROM participants WHERE session_id=%s", (session['user_session'],))
    p = cur.fetchone()
    if p and p['team_id']:
        cur.close()
        conn.close()
        return jsonify({'error': 'Already in a team'}), 400
    cur.execute(
        "UPDATE participants SET team_id=%s WHERE session_id=%s",
        (data['team_id'], session['user_session'])
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/vote', methods=['POST'])
def api_vote():
    if 'user_session' not in session:
        return jsonify({'error': 'No session'}), 400
    data = request.json
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM participants WHERE session_id=%s", (session['user_session'],))
    p = cur.fetchone()
    if not p:
        cur.close(); conn.close()
        return jsonify({'error': 'Not found'}), 404
    if not p['team_id']:
        cur.close(); conn.close()
        return jsonify({'error': 'Not in a team'}), 400
    if p['voted_for']:
        cur.close(); conn.close()
        return jsonify({'error': 'Already voted'}), 400
    if p['team_id'] == data['team_id']:
        cur.close(); conn.close()
        return jsonify({'error': 'Cannot vote for own team'}), 400
    cur.execute(
        "UPDATE participants SET voted_for=%s WHERE session_id=%s",
        (data['team_id'], session['user_session'])
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/my-status')
def api_my_status():
    if 'user_session' not in session:
        return jsonify({'team_id': None, 'voted_for': None})
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT team_id, voted_for FROM participants WHERE session_id=%s", (session['user_session'],))
    p = cur.fetchone()
    cur.close()
    conn.close()
    if p:
        return jsonify({'team_id': p['team_id'], 'voted_for': p['voted_for']})
    return jsonify({'team_id': None, 'voted_for': None})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))