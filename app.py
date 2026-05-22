import os
import sqlite3
import json
import pandas as pd
import plotly.express as px
import plotly.utils
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'gptfx_secure_key_2026'

# --- Database Configuration ---
DATABASE = 'gptfx_mental_health.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            input_text TEXT,
            result_label TEXT,
            confidence REAL,
            explanation TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')
    print("Database initialized.")

# --- GPTFX Core Logic (Simulated GPT-3 Fine-tuned Model) ---
def gptfx_analyze(text):
    """
    In a production environment, this function calls the OpenAI API 
    using a fine-tuned model (e.g., davinci-002 or gpt-3.5-turbo-instruct).
    """
    # Logic: Dual-component Classification & Generation
    # Mock analysis based on keywords for demonstration
    text_lower = text.lower()
    if any(word in text_lower for word in ['hopeless', 'sad', 'tired', 'worthless']):
        label = "Potential Depression"
        confidence = 0.89
        explanation = "The model identified linguistic patterns associated with low self-worth and persistent lethargy, specifically focusing on the term 'hopeless'."
    elif any(word in text_lower for word in ['anxious', 'worry', 'panic', 'heart']):
        label = "High Anxiety"
        confidence = 0.82
        explanation = "Detected high-frequency 'worry' markers and somatic descriptions indicative of physiological arousal."
    else:
        label = "Stable/Neutral"
        confidence = 0.95
        explanation = "The linguistic structure exhibits balanced sentiment and lacks significant indicators of acute mental health distress."
        
    return label, confidence, explanation

# --- Routes ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = request.form['username']
        pw = generate_password_hash(request.form['password'])
        try:
            db = get_db()
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user, pw))
            db.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (request.form['username'],)).fetchone()
        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    analysis = None
    if request.method == 'POST':
        raw_text = request.form['content']
        label, conf, expl = gptfx_analyze(raw_text)
        
        db = get_db()
        db.execute("INSERT INTO assessments (user_id, input_text, result_label, confidence, explanation) VALUES (?,?,?,?,?)",
                   (session['user_id'], raw_text, label, conf, expl))
        db.commit()
        analysis = {'label': label, 'confidence': conf, 'explanation': expl}
        
    return render_template('dashboard.html', analysis=analysis)

@app.route('/reports')
def reports():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.execute("SELECT result_label, timestamp FROM assessments WHERE user_id = ?", (session['user_id'],))
    data = cursor.fetchall()
    
    if not data:
        return render_template('reports.html', plot=None)

    df = pd.DataFrame(data, columns=['Result', 'Date'])
    
    # Create Visualization: Distribution of Mental Health States
    fig = px.pie(df, names='Result', title='Your GPTFX Assessment History', 
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    
    plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('reports.html', plot=plot_json)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
