"""
NeoBank - Application Bancaire de Simulation
Backend Flask avec SQLite
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import random
import string
import uuid
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'neobank-super-secret-key-2025-change-in-prod'

DATABASE = 'instance/neobank.db'

# Créer le dossier instance s'il n'existe pas
if not os.path.exists('instance'):
    os.makedirs('instance')

# Initialiser la base de données au démarrage
with app.app_context():
    init_db()

# ─────────────────────────────────────────────
# Utilitaires Base de Données
# ─────────────────────────────────────────────

def get_db():
    """Retourne une connexion à la base de données SQLite.

    Environnements Cloud Run peuvent démarrer dans un conteneur neuf, donc
    on s'assure que le dossier instance existe avant la connexion.
    """
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialise la base de données avec les tables nécessaires."""
    conn = get_db()
    cursor = conn.cursor()

    # Table des utilisateurs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            balance REAL DEFAULT 0.00,
            card_number TEXT UNIQUE,
            iban TEXT UNIQUE,
            card_virtual_active INTEGER DEFAULT 0,
            account_status TEXT DEFAULT 'active',
            admin_alert TEXT DEFAULT '',
            card_physical_requested INTEGER DEFAULT 0,
            card_approved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Ajouter la colonne admin_alert si elle n'existe pas
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN admin_alert TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass  # Colonne déjà existe

    # Ajouter la colonne card_physical_requested si elle n'existe pas
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN card_physical_requested INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Colonne déjà existe

    # Ajouter la colonne card_approved si elle n'existe pas
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN card_approved INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Colonne déjà existe

    # Table des transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            counterpart TEXT,
            status TEXT DEFAULT 'Terminé',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Ajouter la colonne status si elle n'existe pas
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN status TEXT DEFAULT "Terminé"')
    except sqlite3.OperationalError:
        pass  # Colonne déjà existe

    # Table des notifications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Créer le compte admin s'il n'existe pas
    cursor.execute('SELECT id FROM users WHERE email = ?', ('admin@neobank.io',))
    if not cursor.fetchone():
        admin_hash = generate_password_hash('admin1234')
        cursor.execute('''
            INSERT INTO users (first_name, last_name, email, password_hash, balance, card_number, iban, account_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Admin', 'NeaBank', 'admin@neobank.io', admin_hash, 999999.00, '0000000000000000', 'FR76000000000000000000000000', 'admin'))

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# Générateurs
# ─────────────────────────────────────────────

def generate_card_number():
    """Génère un numéro de carte bancaire fictif de 16 chiffres."""
    prefix = '4'  # Visa fictif
    number = prefix + ''.join([str(random.randint(0, 9)) for _ in range(15)])
    return number


def generate_iban():
    """Génère un IBAN fictif au format français."""
    bank_code = '30006'
    branch_code = ''.join([str(random.randint(0, 9)) for _ in range(5)])
    account_number = ''.join([str(random.randint(0, 9)) for _ in range(11)])
    check_digits = str(random.randint(10, 99))
    return f'FR{check_digits}{bank_code}{branch_code}{account_number}0'


# ─────────────────────────────────────────────
# Décorateurs de Protection
# ─────────────────────────────────────────────

def login_required(f):
    """Vérifie que l'utilisateur est connecté."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Vérifie que l'utilisateur est admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# Routes Principales
# ─────────────────────────────────────────────

@app.route('/')
def index():
    """Landing page."""
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_panel'))
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard utilisateur."""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()

    if not user:
        session.clear()
        return redirect(url_for('index'))

    if user['account_status'] == 'suspended':
        return render_template('suspended.html')

    if user['account_status'] == 'admin':
        return redirect(url_for('admin_panel'))

    return render_template('dashboard.html', user=dict(user))


@app.route('/admin')
@admin_required
def admin_panel():
    """Panel administrateur."""
    return render_template('admin.html')


@app.route('/suspended')
def suspended():
    """Page de compte suspendu."""
    return render_template('suspended.html')


# ─────────────────────────────────────────────
# API Authentification
# ─────────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def api_register():
    """Inscription d'un nouvel utilisateur."""
    data = request.get_json()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not all([first_name, last_name, email, password]):
        return jsonify({'success': False, 'message': 'Tous les champs sont requis.'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Mot de passe trop court (6 caractères min).'}), 400

    conn = get_db()
    try:
        # Vérifier si l'email existe déjà
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Cet email est déjà utilisé.'}), 409

        # Générer les données bancaires
        card_number = generate_card_number()
        iban = generate_iban()
        password_hash = generate_password_hash(password)

        # Insérer l'utilisateur
        cursor = conn.execute('''
            INSERT INTO users (first_name, last_name, email, password_hash, balance, card_number, iban)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (first_name, last_name, email, password_hash, 0.00, card_number, iban))

        user_id = cursor.lastrowid

        # Notification de bienvenue
        conn.execute('''
            INSERT INTO notifications (user_id, message)
            VALUES (?, ?)
        ''', (user_id, f'🎉 Bienvenue chez NeaBank, {first_name} ! Votre compte a été créé avec succès.'))

        conn.commit()

        # Connecter l'utilisateur
        session['user_id'] = user_id
        session['user_name'] = f'{first_name} {last_name}'
        session['is_admin'] = False

        return jsonify({'success': True, 'redirect': '/dashboard'})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Erreur serveur.'}), 500
    finally:
        conn.close()


@app.route('/api/login', methods=['POST'])
def api_login():
    """Connexion d'un utilisateur."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'success': False, 'message': 'Email ou mot de passe incorrect.'}), 401

    # Vérifier si suspendu
    if user['account_status'] == 'suspended':
        session['user_id'] = user['id']
        session['is_admin'] = False
        return jsonify({'success': True, 'redirect': '/suspended'})

    session['user_id'] = user['id']
    session['user_name'] = f"{user['first_name']} {user['last_name']}"
    session['is_admin'] = (user['account_status'] == 'admin')

    redirect_url = '/admin' if session['is_admin'] else '/dashboard'
    return jsonify({'success': True, 'redirect': redirect_url})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Déconnexion."""
    session.clear()
    return jsonify({'success': True})


# ─────────────────────────────────────────────
# API Utilisateur
# ─────────────────────────────────────────────

@app.route('/api/me', methods=['GET'])
@login_required
def api_me():
    """Retourne les données de l'utilisateur connecté."""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if not user:
        conn.close()
        session.clear()
        return jsonify({'success': False}), 401

    # Vérifier si suspendu
    if user['account_status'] == 'suspended':
        conn.close()
        return jsonify({'success': False, 'suspended': True}), 403

    # Transactions récentes
    transactions = conn.execute('''
        SELECT * FROM transactions WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 10
    ''', (session['user_id'],)).fetchall()

    # Notifications non lues
    notifications = conn.execute('''
        SELECT * FROM notifications WHERE user_id = ? AND is_read = 0
        ORDER BY created_at DESC LIMIT 5
    ''', (session['user_id'],)).fetchall()

    conn.close()

    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'email': user['email'],
            'balance': user['balance'],
            'card_number': user['card_number'],
            'iban': user['iban'],
            'card_virtual_active': bool(user['card_virtual_active']),
            'account_status': user['account_status'],
            'admin_alert': user['admin_alert'],
            'card_approved': bool(user['card_approved']),
            'created_at': user['created_at']
        },
        'transactions': [dict(t) for t in transactions],
        'notifications': [dict(n) for n in notifications]
    })


@app.route('/api/transfer', methods=['POST'])
@login_required
def api_transfer():
    """Effectue un virement."""
    data = request.get_json()
    iban_dest = data.get('iban', '').strip()
    amount = float(data.get('amount', 0))
    description = data.get('description', 'Virement').strip()

    if amount <= 0:
        return jsonify({'success': False, 'message': 'Montant invalide.'}), 400

    conn = get_db()
    try:
        sender = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if sender['balance'] < amount:
            return jsonify({'success': False, 'message': 'Solde insuffisant.'}), 400

        # Chercher le destinataire par IBAN
        recipient = conn.execute('SELECT * FROM users WHERE iban = ?', (iban_dest,)).fetchone()

        # Débiter l'expéditeur
        conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, session['user_id']))

        # Enregistrer la transaction sortante
        conn.execute('''
            INSERT INTO transactions (user_id, type, amount, description, counterpart, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], 'DEBIT', amount, description, iban_dest, 'En cours'))

        # Si le destinataire est dans notre système, créditer
        if recipient and recipient['id'] != sender['id']:
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, recipient['id']))
            conn.execute('''
                INSERT INTO transactions (user_id, type, amount, description, counterpart, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (recipient['id'], 'CREDIT', amount, description, sender['iban'], 'Terminé'))

            # Notification au destinataire
            conn.execute('''
                INSERT INTO notifications (user_id, message)
                VALUES (?, ?)
            ''', (recipient['id'], f'💸 Vous avez reçu {amount:.2f} € de {sender["first_name"]} {sender["last_name"]}'))

        conn.commit()

        # Récupérer le nouveau solde
        updated = conn.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        return jsonify({'success': True, 'new_balance': updated['balance']})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Erreur lors du virement.'}), 500
    finally:
        conn.close()


@app.route('/api/toggle-virtual-card', methods=['POST'])
@login_required
def api_toggle_virtual_card():
    """Active/désactive la carte virtuelle."""
    conn = get_db()
    user = conn.execute('SELECT card_virtual_active FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    new_status = 0 if user['card_virtual_active'] else 1
    conn.execute('UPDATE users SET card_virtual_active = ? WHERE id = ?', (new_status, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'active': bool(new_status)})


@app.route('/api/transaction/cancel', methods=['POST'])
@login_required
def api_transaction_cancel():
    """Annule une transaction en cours."""
    data = request.get_json()
    transaction_id = data.get('transaction_id')

    conn = get_db()
    try:
        # Vérifier que la transaction appartient à l'utilisateur et est 'En cours'
        tx = conn.execute('''
            SELECT * FROM transactions WHERE id = ? AND user_id = ? AND status = 'En cours'
        ''', (transaction_id, session['user_id'])).fetchone()

        if not tx:
            return jsonify({'success': False, 'message': 'Transaction introuvable ou non annulable.'}), 404

        # Annuler la transaction : rembourser le solde et changer status
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (tx['amount'], session['user_id']))
        conn.execute('UPDATE transactions SET status = ? WHERE id = ?', ('Annulé', transaction_id))

        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Erreur lors de l\'annulation.'}), 500
    finally:
        conn.close()


@app.route('/api/order-physical-card', methods=['POST'])
@login_required
def api_order_physical_card():
    """Demander une carte physique."""
    conn = get_db()
    try:
        # Vérifier si déjà demandé
        user = conn.execute('SELECT card_physical_requested FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if user['card_physical_requested']:
            return jsonify({'success': False, 'message': 'Demande déjà en cours.'}), 400

        # Marquer comme demandé
        conn.execute('UPDATE users SET card_physical_requested = 1 WHERE id = ?', (session['user_id'],))

        # Notification à l'admin
        conn.execute('''
            INSERT INTO notifications (user_id, message)
            VALUES (?, ?)
        ''', (1, f'📬 Nouvelle demande de carte physique de {session["user_name"]}'))  # user_id 1 pour admin

        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Erreur.'}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API Admin
# ─────────────────────────────────────────────

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def api_admin_users():
    """Liste tous les utilisateurs (sauf admin)."""
    conn = get_db()
    users = conn.execute('''
        SELECT id, first_name, last_name, email, balance, card_number, iban,
               account_status, created_at, admin_alert, card_physical_requested, card_approved
        FROM users WHERE account_status != 'admin'
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    return jsonify({'success': True, 'users': [dict(u) for u in users]})


@app.route('/api/admin/update-balance', methods=['POST'])
@admin_required
def api_admin_update_balance():
    """Modifie le solde d'un utilisateur (virement créditeur)."""
    data = request.get_json()
    user_id = data.get('user_id')
    amount = float(data.get('amount', 0))
    sender_name = data.get('sender_name', 'Admin').strip()

    if amount <= 0:
        return jsonify({'success': False, 'message': 'Montant invalide.'}), 400

    conn = get_db()
    try:
        # Créditer le solde
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, user_id))

        # Créer la transaction
        conn.execute('''
            INSERT INTO transactions (user_id, type, amount, description, counterpart, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, 'CREDIT', amount, f'Virement reçu de {sender_name}', sender_name, 'Terminé'))

        # Notification automatique
        conn.execute('''
            INSERT INTO notifications (user_id, message)
            VALUES (?, ?)
        ''', (user_id, f'💰 Virement reçu : +{amount:.2f} € de {sender_name}'))

        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Erreur lors de la mise à jour.'}), 500
    finally:
        conn.close()


@app.route('/api/admin/notify', methods=['POST'])
@admin_required
def api_admin_notify():
    """Envoie une notification personnalisée à un utilisateur."""
    data = request.get_json()
    user_id = data.get('user_id')
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'success': False, 'message': 'Message vide.'}), 400

    conn = get_db()
    conn.execute('INSERT INTO notifications (user_id, message) VALUES (?, ?)', (user_id, message))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/admin/toggle-status', methods=['POST'])
@admin_required
def api_admin_toggle_status():
    """Suspend ou réactive un compte utilisateur."""
    data = request.get_json()
    user_id = data.get('user_id')

    conn = get_db()
    user = conn.execute('SELECT account_status FROM users WHERE id = ?', (user_id,)).fetchone()

    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'Utilisateur introuvable.'}), 404

    new_status = 'suspended' if user['account_status'] == 'active' else 'active'
    conn.execute('UPDATE users SET account_status = ? WHERE id = ?', (new_status, user_id))

    # Notification si suspension
    if new_status == 'suspended':
        conn.execute('''
            INSERT INTO notifications (user_id, message)
            VALUES (?, ?)
        ''', (user_id, '🚫 Votre compte a été suspendu. Contactez le support.'))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'new_status': new_status})


@app.route('/api/admin/approve-card', methods=['POST'])
@admin_required
def api_admin_approve_card():
    """Approuver la carte d'un utilisateur."""
    data = request.get_json()
    user_id = data.get('user_id')

    conn = get_db()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'Utilisateur introuvable.'}), 404

        if user['card_approved']:
            return jsonify({'success': False, 'message': 'Carte déjà approuvée.'}), 400

        # Approuver la carte
        conn.execute('UPDATE users SET card_approved = 1 WHERE id = ?', (user_id,))

        # Notification au client
        conn.execute('''
            INSERT INTO notifications (user_id, message)
            VALUES (?, ?)
        ''', (user_id, '🎉 Votre carte bancaire a été approuvée et est maintenant active !'))

        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Erreur.'}), 500
    finally:
        conn.close()


@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def api_admin_stats():
    """Statistiques globales de la plateforme."""
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE account_status != 'admin'").fetchone()['c']
    active_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE account_status = 'active'").fetchone()['c']
    suspended_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE account_status = 'suspended'").fetchone()['c']
    total_balance = conn.execute("SELECT COALESCE(SUM(balance), 0) as s FROM users WHERE account_status != 'admin'").fetchone()['s']
    total_transactions = conn.execute("SELECT COUNT(*) as c FROM transactions").fetchone()['c']
    conn.close()

    return jsonify({
        'success': True,
        'stats': {
            'total_users': total_users,
            'active_users': active_users,
            'suspended_users': suspended_users,
            'total_balance': total_balance,
            'total_transactions': total_transactions
        }
    })


# ─────────────────────────────────────────────
# Lancement
# ─────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print(f"✅ NeaBank démarré sur http://0.0.0.0:{port}")
    print("📧 Admin: admin@neobank.io | Mot de passe: admin1234")
    app.run(host='0.0.0.0', port=port)
