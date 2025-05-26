from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np
import joblib

app = Flask(__name__)
app.secret_key = 'npk'

model = joblib.load("models/sugarcane_yield_model.pkl")  # your model path
scaler = joblib.load("models/sugarcane_scalar.pkl")  # your scaler path


def init_db():
    with sqlite3.connect('users.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
init_db()



def generate_recommendations(N, P, K, predicted_fertility):
    if predicted_fertility >= 13:
        return (
            "✅ Soil fertility is in excellent condition!<br>"
            "🧪 Continue regular testing and maintain pH balance.<br>"
            "🌿 Use green manure and crop rotation to retain long-term fertility.<br>"
            "💧 Ensure proper irrigation and avoid overuse of fertilizers."
        )

    messages = ["⚠️ Fertility is below the optimal threshold (12). Soil improvement is needed:"]

    if N < 5:
        messages.append("🟨 **Low Nitrogen (N):** Apply urea, ammonium sulfate, composted manure, or grow leguminous cover crops like clover or alfalfa.")
    if P < 5:
        messages.append("🟦 **Low Phosphorus (P):** Use single super phosphate (SSP), bone meal, or rock phosphate. Ensure proper soil drainage.")
    if K < 5:
        messages.append("🟥 **Low Potassium (K):** Apply muriate of potash (MOP), wood ash, or compost with banana peels/potato peels.")

    # Additional general practices
    messages.append("🌾 Use organic compost and mulching to improve overall soil structure and moisture retention.")
    messages.append("🌿 Rotate crops and include green manures like sunhemp or dhaincha to replenish soil nutrients.")
    messages.append("📈 Regularly monitor soil pH and EC. Use gypsum or lime to balance acidic/alkaline conditions if needed.")

    return "<br>".join(messages)


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        with sqlite3.connect('users.db') as conn:
            try:
                conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
                conn.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Email already exists.', 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        with sqlite3.connect('users.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE name = ?", (name,))
            user = cur.fetchone()
            if user and check_password_hash(user[3], password):
                session['user'] = user[1]
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid name or password', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('dashboard.html', username=session['user'])
    return redirect(url_for('login'))




@app.route("/ml")
def index():
    return render_template("form.html")


@app.route("/predict", methods=["POST"])
def predict():
    try:
        # Extract inputs
        N = float(request.form["N"])
        P = float(request.form["P"])
        K = float(request.form["K"])
        EC = float(request.form["EC"])
        pH = float(request.form["pH"])
        temperature = float(request.form["temperature"])
        humidity = float(request.form["humidity"])

        # Prepare and scale data
        data = np.array([[N, P, K, EC, pH, temperature, humidity]])
        scaled = scaler.transform(data)

        # Predict fertility level
        prediction = model.predict(scaled)[0] + 1  # Shift from 0–14 to 1–15
        prediction_text = f"🌾 Predicted Sugarcane Fertility Level: {int(prediction)} (1 = Low, 15 = High)"

        # Only give recommendations if below optimum (12)
        recommendation_text = generate_recommendations(N, P, K, prediction)

        return render_template("form.html", prediction_text=prediction_text, recommendation_text=recommendation_text)

    except Exception as e:
        return render_template("form.html", prediction_text="⚠️ Error: Invalid input or model issue.")


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
