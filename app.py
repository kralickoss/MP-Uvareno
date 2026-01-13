from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import os
import json
import time
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'tajny_klic_pro_session_brasko_zmen_si_ho'  # Důležité pro přihlášení!

# --- NASTAVENÍ ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB upload

# Vytvoření složky pro obrázky, pokud neexistuje
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DATABÁZE (SQLite) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "recepty.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Tabulka Uživatelů
    c.execute('''
        CREATE TABLE IF NOT EXISTS uzivatele (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jmeno TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            heslo TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            datum_registrace TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Tabulka Receptů (s odkazem na autora)
    c.execute('''
        CREATE TABLE IF NOT EXISTS recepty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            autor_id INTEGER,
            nazev TEXT NOT NULL,
            popis TEXT,
            kategorie TEXT,
            obtiznost TEXT,
            cas_pripravy INTEGER,
            maso TEXT,
            pikantnost TEXT,
            tip TEXT,
            obrazek TEXT,
            ingredience TEXT, 
            postup TEXT,
            datum_pridani TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(autor_id) REFERENCES uzivatele(id)
        )
    ''')

    # 3. Tabulka Hodnocení
    c.execute('''
        CREATE TABLE IF NOT EXISTS hodnoceni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uzivatel_id INTEGER,
            recept_id INTEGER,
            hvezdy INTEGER,
            FOREIGN KEY(uzivatel_id) REFERENCES uzivatele(id),
            FOREIGN KEY(recept_id) REFERENCES recepty(id)
        )
    ''')

    # Vytvoření ADMINA, pokud neexistuje
    try:
        c.execute("SELECT * FROM uzivatele WHERE jmeno = 'admin'")
        if not c.fetchone():
            print("👑 Vytvářím admin účet...")
            hash_heslo = generate_password_hash("admin")
            c.execute("INSERT INTO uzivatele (jmeno, email, heslo, role) VALUES (?, ?, ?, ?)", 
                      ("admin", "admin@uvareno.cz", hash_heslo, "admin"))
    except Exception as e:
        print(f"Chyba admina: {e}")

    conn.commit()
    conn.close()

# Inicializace DB při startu
init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Abychom mohli brát data podle názvu sloupců
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- TRASY PRO HTML (ROUTING) ---
@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

@app.route('/recepty.html')
def recepty():
    return render_template('recepty.html')

@app.route('/login.html')
def login():
    return render_template('login.html')

@app.route('/detail.html')
def detail():
    return render_template('detail.html')

@app.route('/pridat-recept.html')
def pridat_recept():
    # Ochrana: Jen přihlášený může přidat recept
    if 'user_id' not in session:
        return redirect('/login.html')
    return render_template('pridat-recept.html')

@app.route('/admin.html')
def admin_panel():
    # Ochrana: Jen admin může sem
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/')
    return render_template('admin.html')


# --- API: AUTENTIZACE ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    jmeno = data.get('jmeno')
    email = data.get('email')
    heslo = data.get('heslo')

    if not all([jmeno, email, heslo]):
        return jsonify({'success': False, 'message': 'Vyplň všechna pole!'}), 400

    hashed_pw = generate_password_hash(heslo)

    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO uzivatele (jmeno, email, heslo) VALUES (?, ?, ?)", (jmeno, email, hashed_pw))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Registrace úspěšná! Nyní se přihlas.'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Jméno nebo email už existuje.'}), 400

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    jmeno = data.get('jmeno')
    heslo = data.get('heslo')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM uzivatele WHERE jmeno = ?", (jmeno,))
    user = c.fetchone()
    conn.close()
    
    # 1. Kontrola existence uživatele
    if not user:
        return jsonify({'success': False, 'message': 'Tento účet neexistuje. Musíš se nejdřív registrovat!'}), 401

    # 2. Kontrola hesla
    if not check_password_hash(user['heslo'], heslo):
        return jsonify({'success': False, 'message': 'Zadal jsi špatné heslo, zkus to znovu.'}), 401
    
    # 3. Login OK
    session['user_id'] = user['id']
    session['jmeno'] = user['jmeno']
    session['role'] = user['role']
    return jsonify({'success': True, 'role': user['role']})

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect('/')

# --- API: RECEPTY ---
@app.route('/api/pridat-recept', methods=['POST'])
def api_pridat_recept():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Musíš být přihlášen!'}), 401

    try:
        nazev = request.form.get('nazev')
        popis = request.form.get('popis')
        kategorie = request.form.get('kategorie')
        obtiznost = request.form.get('obtiznost')
        cas = request.form.get('cas')
        maso = request.form.get('maso')
        pikantnost = request.form.get('pikantnost')
        tip = request.form.get('tip')
        ingredience = request.form.get('ingredience')
        postup = request.form.get('postup')

        # Kontrola povinných polí
        if not all([nazev, popis, kategorie, obtiznost, cas, maso, pikantnost]):
             return jsonify({'success': False, 'message': 'Chybí povinná pole! Vyplň to pořádně, bráško.'}), 400

        file = request.files.get('obrazek')
        
        # Defaultní obrázek, pokud uživatel žádný nenahraje
        filename_db = "static/assets/poklop.png" 

        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            unique_filename = f"{int(time.time())}_{original_filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            filename_db = f"static/uploads/{unique_filename}"

        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """INSERT INTO recepty (autor_id, nazev, popis, kategorie, obtiznost, cas_pripravy, maso, pikantnost, tip, obrazek, ingredience, postup) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        
        val = (session['user_id'], nazev, popis, kategorie, obtiznost, cas, maso, pikantnost, tip, filename_db, ingredience, postup)
        
        cursor.execute(sql, val)
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Recept uložen!'})
    except Exception as e:
        print(f"❌ Chyba při ukládání: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Získáme recepty + průměrné hodnocení
    cursor.execute("""
        SELECT r.*, AVG(h.hvezdy) as prumer 
        FROM recepty r 
        LEFT JOIN hodnoceni h ON r.id = h.recept_id 
        GROUP BY r.id 
        ORDER BY datum_pridani DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    recipes_list = []
    for row in rows:
        rating = row["prumer"] if row["prumer"] else 0
        # Ošetření chybějícího obrázku i při čtení
        img_path = row["obrazek"] if row["obrazek"] else "static/assets/poklop.png"
        
        recipes_list.append({
            "id": row["id"],
            "name": row["nazev"],
            "category": row["kategorie"],
            "difficulty": row["obtiznost"],
            "time": row["cas_pripravy"],
            "rating": round(rating), 
            "image": img_path
        })
    return jsonify(recipes_list)

# --- V app.py ---
@app.route('/api/recipe/<int:id>', methods=['GET'])
def get_recipe_detail(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Získáme detail + jméno autora + průměr hodnocení
    cursor.execute("""
        SELECT r.*, u.jmeno as autor_jmeno, AVG(h.hvezdy) as prumer 
        FROM recepty r
        LEFT JOIN uzivatele u ON r.autor_id = u.id
        LEFT JOIN hodnoceni h ON r.id = h.recept_id
        WHERE r.id = ?
        GROUP BY r.id
    """, (id,))
    row = cursor.fetchone()

    # Zjistit, jestli uživatel už hodnotil (pokud je přihlášen)
    user_rating = 0
    can_rate = False
    if 'user_id' in session:
        can_rate = True
        cursor.execute("SELECT hvezdy FROM hodnoceni WHERE recept_id = ? AND uzivatel_id = ?", (id, session['user_id']))
        rating_row = cursor.fetchone()
        if rating_row:
            user_rating = rating_row['hvezdy']

    conn.close()

    if row:
        try: ing = json.loads(row["ingredience"])
        except: ing = []
        try: pos = json.loads(row["postup"])
        except: pos = []

        img_path = row["obrazek"] if row["obrazek"] else "static/assets/poklop.png"

        recipe_data = {
            "id": row["id"],
            "name": row["nazev"],
            "desc": row["popis"],
            "category": row["kategorie"],
            "difficulty": row["obtiznost"],
            "time": row["cas_pripravy"],
            "rating": round(row["prumer"] if row["prumer"] else 0, 1),
            "image": img_path,
            "ingredients": ing,
            "steps": pos,
            "tip": row["tip"],
            "pikantnost": row["pikantnost"],
            "maso": row["maso"],
            "author": row["autor_jmeno"] if row["autor_jmeno"] else "Neznámý kuchař",
            "user_rating": user_rating,
            "can_rate": can_rate
        }
        return jsonify(recipe_data)
    else:
        return jsonify({"error": "Recept nenalezen"}), 404

# --- API: HODNOCENÍ ---
@app.route('/api/rate', methods=['POST'])
def rate_recipe():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Musíš být přihlášen!'}), 401
    
    data = request.json
    recept_id = data.get('id')
    stars = data.get('stars')

    conn = get_db_connection()
    c = conn.cursor()
    
    # Zkontrolujeme, jestli už hodnotil -> Update nebo Insert
    c.execute("SELECT id FROM hodnoceni WHERE uzivatel_id = ? AND recept_id = ?", (session['user_id'], recept_id))
    exists = c.fetchone()
    
    if exists:
        c.execute("UPDATE hodnoceni SET hvezdy = ? WHERE id = ?", (stars, exists['id']))
    else:
        c.execute("INSERT INTO hodnoceni (uzivatel_id, recept_id, hvezdy) VALUES (?, ?, ?)", (session['user_id'], recept_id, stars))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# --- API: ADMIN DATA (UPDATE) ---
@app.route('/api/admin/data')
def admin_data():
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Načíst uživatele
    c.execute("SELECT id, jmeno, email, role FROM uzivatele")
    users = [dict(row) for row in c.fetchall()]
    
    # 2. Načíst recepty I S AUTOREM
    c.execute("""
        SELECT r.id, r.nazev, u.jmeno as autor 
        FROM recepty r
        LEFT JOIN uzivatele u ON r.autor_id = u.id
    """)
    recipes = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({'users': users, 'recipes': recipes})

@app.route('/api/admin/delete/<type>/<int:id>', methods=['DELETE'])
def admin_delete(type, id):
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    c = conn.cursor()
    
    if type == 'user':
        # Nesmazat sám sebe
        if id == session['user_id']:
            return jsonify({'success': False, 'message': 'Nemůžeš smazat sám sebe!'}), 400
        c.execute("DELETE FROM uzivatele WHERE id = ?", (id,))
        # Volitelně by šlo smazat i recepty tohoto uživatele
    elif type == 'recipe':
        c.execute("DELETE FROM recepty WHERE id = ?", (id,))
        c.execute("DELETE FROM hodnoceni WHERE recept_id = ?", (id,))
        
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# --- API: KDO JSEM? (PRO NAVBAR) ---
@app.route('/api/me')
def api_me():
    if 'user_id' in session:
        return jsonify({
            'logged_in': True, 
            'jmeno': session['jmeno'], 
            'role': session.get('role', 'user'),
            'id': session['user_id']
        })
    return jsonify({'logged_in': False})

if __name__ == '__main__':
    app.run(debug=True)