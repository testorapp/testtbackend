import os
import secrets
import re
from datetime import datetime
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_mail import Mail, Message

load_dotenv()

app = Flask(__name__)

print("RUNNING:", __file__) # FIXED: Explicit CORS for /api/* to handle OPTIONS preflight properly
# ==================== CORS ====================

ALLOWED_ORIGINS = [
    "https://testorapp.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500"
]

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")

    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"

    return response

@app.route("/api/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return ("", 204)

# Session config for cross-origin cookies
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Database
database_url = os.environ.get("DATABASE_URL", "sqlite:///testora.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

print("DATABASE URL:", database_url)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Email config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'testora.inc@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'testora.inc@gmail.com')

mail = Mail(app)
db = SQLAlchemy(app)

FRONTEND_URL = "https://testorapp.github.io"

# ==================== MODELS ====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)   # FIXED: was Te50
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    activation_token = db.Column(db.String(64), unique=True)
    reset_token = db.Column(db.String(64), unique=True)     # FIXED: separate column
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== VALIDATORS ====================

def validate_name(name):
    if not name or len(name) < 2 or len(name) > 50:
        return False
    return bool(re.match(r"^[a-zA-Z\s\-\']+$", name))

def validate_password(password):
    if not password or len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password): return False
    if not re.search(r'[a-z]', password): return False
    if not re.search(r'\d', password): return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password): return False
    return True

def validate_email(email):
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# ==================== EMAIL HELPERS ====================

def send_activation_email(user):
    activation_token = secrets.token_urlsafe(32)
    user.activation_token = activation_token
    db.session.commit()

    activation_url = f"{FRONTEND_URL}/activate.html?token={activation_token}"

    msg = Message(
        subject="Activate your Testora Account",
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email]
    )
    msg.body = "Welcome to Testora! Please activate your account."
    msg.html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:30px 10px;">
<tr><td align="center">
<table width="540" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
<tr><td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:32px 40px;text-align:center;">
<h1 style="margin:0;color:#fff;font-size:24px;">Testora</h1>
<p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Test Sites. Get Paid</p>
</td></tr>
<tr><td style="padding:36px 40px;">
<h2 style="margin:0 0 16px;color:#333;font-size:20px;">Welcome to Testora!</h2>
<p style="margin:0 0 20px;color:#555;font-size:15px;line-height:1.6;">Thank you for registering. Click the button below to verify your email.</p>
<table cellpadding="0" cellspacing="0" style="margin:0 0 24px;"><tr>
<td align="center" style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:6px;">
<a href="{activation_url}" style="display:inline-block;padding:14px 36px;color:#fff;font-size:16px;font-weight:600;text-decoration:none;">ACTIVATE ACCOUNT</a>
</td></tr></table>
<p style="margin:0;color:#999;font-size:12px;">If you didn't create an account, please ignore this email.</p>
</td></tr>
<tr><td style="padding:20px 40px;background:#fafafa;border-top:1px solid #eee;text-align:center;">
<p style="margin:0;color:#aaa;font-size:12px;">&copy; 2024 Testora. All rights reserved.</p>
</td></tr>
</table></td></tr></table></body></html>"""

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send activation email: {e}")
        return False

def send_reset_email(user, reset_token):
    reset_url = f"{FRONTEND_URL}/reset-password.html?token={reset_token}"

    msg = Message(
        subject="Reset Your Testora Password",
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email]
    )
    msg.body = "You requested a password reset."
    msg.html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:30px 10px;">
<tr><td align="center">
<table width="540" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
<tr><td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:32px 40px;text-align:center;">
<h1 style="margin:0;color:#fff;font-size:24px;">Testora</h1>
</td></tr>
<tr><td style="padding:36px 40px;">
<h2 style="margin:0 0 16px;color:#333;font-size:20px;">Reset Your Password</h2>
<p style="margin:0 0 20px;color:#555;font-size:15px;line-height:1.6;">Click the button below to create a new password.</p>
<table cellpadding="0" cellspacing="0" style="margin:0 0 24px;"><tr>
<td align="center" style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:6px;">
<a href="{reset_url}" style="display:inline-block;padding:14px 36px;color:#fff;font-size:16px;font-weight:600;text-decoration:none;">RESET PASSWORD</a>
</td></tr></table>
<p style="margin:0;color:#999;font-size:12px;">If you didn't request this, please ignore this email.</p>
</td></tr>
<tr><td style="padding:20px 40px;background:#fafafa;border-top:1px solid #eee;text-align:center;">
<p style="margin:0;color:#aaa;font-size:12px;">&copy; 2024 Testora. All rights reserved.</p>
</td></tr>
</table></td></tr></table></body></html>"""

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send reset email: {e}")
        return False

# ==================== ROUTES ====================

@app.route('/')
def index():
    return jsonify({
        "message": "Testora API",
        "status": "live",
        "endpoints": [
            "/api/register", "/api/login", "/api/logout",
            "/api/user", "/api/sites", "/api/stats",
            "/api/activate/<token>", "/api/resend-activation",
            "/api/forgot-password", "/api/reset-password/<token>"
        ]
    })

@app.route('/api/stats')
def get_stats():
    stats = [
        {"label": "COMMUNITY EARNINGS", "value": "$2.4M+", "change": "+12.4%", "change_label": "this month"},
        {"label": "SITES TESTED", "value": "150,000+", "change": "+8.1%", "change_label": "vs last quarter"},
        {"label": "ACTIVE TESTERS", "value": "45,000+", "change": "+15.7%", "change_label": "growth"}
    ]
    return jsonify({"success": True, "stats": stats})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    terms = data.get('terms', False)

    errors = []
    if not validate_name(first_name):
        errors.append("First name must be 2-50 characters, letters only.")
    if not validate_name(last_name):
        errors.append("Last name must be 2-50 characters, letters only.")
    if not validate_email(email):
        errors.append("Please enter a valid email address.")
    if not validate_password(password):
        errors.append("Password must be at least 8 characters with uppercase, lowercase, number, and special character.")
    if password != confirm_password:
        errors.append("Passwords do not match.")
    if not terms:
        errors.append("You must agree to the Terms of Service.")

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        if existing_user.is_active:
            return jsonify({"success": False, "error": "An account with this email already exists. Please log in."}), 409
        else:
            sent = send_activation_email(existing_user)
            if sent:
                return jsonify({"success": True, "message": "Account exists but is not activated. A new activation link has been sent."}), 200
            else:
                return jsonify({"success": False, "error": "Could not send activation email. Please try again later."}), 500

    password_hash = generate_password_hash(password)

    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=password_hash,
        is_active=False
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        sent = send_activation_email(new_user)
        if sent:
            return jsonify({"success": True, "message": "Registration successful! Please check your email to activate your account."}), 201
        else:
            return jsonify({"success": True, "message": "Account created but we could not send the activation email. Please use Resend Activation."}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {e}")
        return jsonify({"success": False, "error": "An error occurred. Please try again."}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()

    if user and user.is_active:
        if check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['first_name'] = user.first_name
            return jsonify({
                "success": True,
                "message": f"Welcome back, {user.first_name}!",
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email
                }
            })
        else:
            return jsonify({"success": False, "error": "Invalid email or password."}), 401
    elif user and not user.is_active:
        return jsonify({"success": False, "error": "Your account is not activated. Please check your email."}), 403
    else:
        return jsonify({"success": False, "error": "Invalid email or password."}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "You have been logged out successfully."})

@app.route('/api/user')
def get_user():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Please log in."}), 401

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({"success": False, "error": "User not found."}), 404

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_active": user.is_active
        },
        "stats": {
            "earnings": 0.00,
            "tests_completed": 0,
            "pending_tests": 0
        }
    })

@app.route('/api/activate/<token>')
def activate(token):
    user = User.query.filter_by(activation_token=token).first()

    if user:
        if user.is_active:
            return jsonify({"success": True, "message": "Your account is already activated. Please log in.", "already_active": True})
        else:
            user.is_active = True
            user.activation_token = None
            db.session.commit()
            return jsonify({"success": True, "message": "Your account has been activated successfully! You can now log in."})
    else:
        return jsonify({"success": False, "error": "Invalid activation link. Please request a new activation email."}), 400

@app.route('/api/resend-activation', methods=['POST'])
def resend_activation():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "error": "Please enter your email address."}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"success": False, "error": "No account found with this email address."}), 404
    elif user.is_active:
        return jsonify({"success": True, "message": "This account is already activated. Please log in.", "already_active": True})
    else:
        sent = send_activation_email(user)
        if sent:
            return jsonify({"success": True, "message": "A new activation link has been sent to your email."})
        else:
            return jsonify({"success": False, "error": "Could not send email. Please try again later."}), 500

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "error": "Please enter your email address."}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"success": False, "error": "No account found with this email address."}), 404

    # FIXED: Use reset_token instead of overwriting activation_token
    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    db.session.commit()

    sent = send_reset_email(user, reset_token)
    if sent:
        return jsonify({"success": True, "message": "A password reset link has been sent to your email."})
    else:
        return jsonify({"success": False, "error": "Could not send reset email. Please try again later."}), 500

@app.route('/api/reset-password/<token>', methods=['POST'])
def reset_password(token):
    # FIXED: Look up by reset_token, not activation_token
    user = User.query.filter_by(reset_token=token).first()

    if not user:
        return jsonify({"success": False, "error": "Invalid or expired reset link. Please request a new password reset."}), 400

    data = request.get_json() or {}
    new_password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not new_password or not confirm_password:
        return jsonify({"success": False, "error": "Please fill in all fields."}), 400

    if new_password != confirm_password:
        return jsonify({"success": False, "error": "Passwords do not match."}), 400

    if not validate_password(new_password):
        return jsonify({"success": False, "error": "Password must be at least 8 characters with uppercase, lowercase, number, and special character."}), 400

    user.password_hash = generate_password_hash(new_password)
    user.reset_token = None  # FIXED: clear reset_token, not activation_token
    db.session.commit()

    return jsonify({"success": True, "message": "Your password has been reset successfully! You can now log in."})

@app.route('/api/sites')
def get_sites():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Please log in to access this page."}), 401

    sites = [
        {"id": 1, "name": "Quartze", "pay": "$12.00", "status": "Active", "url": "https://sites.google.com/view/quartze"},
        {"id": 2, "name": "Playable", "pay": "$15.00", "status": "Active", "url": "https://sites.google.com/view/quartze"},
        {"id": 3, "name": "Optilink", "pay": "$10.00", "status": "Active", "url": "https://sites.google.com/view/quartze"},
        {"id": 4, "name": "Tundra", "pay": "$18.00", "status": "Active", "url": "https://sites.google.com/view/quartze"},
        {"id": 5, "name": "Blooxe", "pay": "$14.00", "status": "Active", "url": "https://sites.google.com/view/quartze"},
        {"id": 6, "name": "Nexus", "pay": "$11.00", "status": "Active", "url": "https://sites.google.com/view/quartze"},
        {"id": 7, "name": "Vortex", "pay": "$9.00", "status": "Active", "url": "https://sites.google.com/view/quartze"},
        {"id": 8, "name": "Zenith", "pay": "$13.00", "status": "Active", "url": "https://sites.google.com/view/quartze"},
    ]

    return jsonify({"success": True, "sites": sites})

# ==================== INIT ====================

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5001)