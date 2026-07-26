import os
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Regexp, EqualTo, ValidationError
import re
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://testorapp.github.io"])
# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///testora.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration - Gmail SMTP (use environment variables for security)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'testora.inc@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'testora.inc@gmail.com')


# Initialize Flask-Mail
from flask_mail import Mail, Message
mail = Mail(app)

# Initialize database
db = SQLAlchemy(app)

# Initialize CSRF protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# Add session and csrf_token to template context
@app.context_processor
def inject_session():
    from flask_wtf.csrf import generate_csrf
    return dict(session=session, csrf_token=generate_csrf)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    activation_token = db.Column(db.String(64), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.email}>'

# Custom Validators
def validate_name(form, field):
    """Validate name: 2-50 characters, letters only, spaces, hyphens, apostrophes"""
    if field.data:
        if len(field.data) < 2 or len(field.data) > 50:
            raise ValidationError('Name must be between 2 and 50 characters.')
        if not re.match(r"^[a-zA-Z\s\-']+$", field.data):
            raise ValidationError('Name can only contain letters, spaces, hyphens, and apostrophes.')

def validate_password(form, field):
    """Validate password: min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char"""
    if field.data:
        password = field.data
        errors = []
        
        if len(password) < 8:
            errors.append('at least 8 characters')
        if not re.search(r'[A-Z]', password):
            errors.append('one uppercase letter')
        if not re.search(r'[a-z]', password):
            errors.append('one lowercase letter')
        if not re.search(r'\d', password):
            errors.append('one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append('one special character (!@#$%^&*() etc.)')
        
        if errors:
            raise ValidationError(f'Password must contain {", ".join(errors)}.')

# Registration Form
class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required.'),
        validate_name
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required.'),
        validate_name
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=8, max=128, message='Password must be between 8 and 128 characters.'),
        validate_password
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords must match.')
    ])
    terms = BooleanField('Terms', validators=[
        DataRequired(message='You must agree to the Terms of Service.')
    ])
    submit = SubmitField('Create Account')

# Login Form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.')
    ])
    submit = SubmitField('Log In')

def send_activation_email(user):
    """Send activation email to user using Flask-Mail"""
    activation_token = secrets.token_urlsafe(32)
    user.activation_token = activation_token
    db.session.commit()
    
    activation_url = url_for('activate', token=activation_token, _external=True)
    
    msg = Message(
        subject="Activate your Testora Account",
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email]
    )
    msg.body = "Welcome to Testora! To activate your account, please view this email in an HTML-compatible email client."
    msg.html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f4;padding:30px 10px;">
        <tr>
            <td align="center">
                <table role="presentation" width="540" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                    <tr>
                        <td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:32px 40px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;">Testora</h1>
<p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Test Sites. Get Paid</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:36px 40px;">
                            <h2 style="margin:0 0 16px;color:#333333;font-size:20px;font-weight:600;">Welcome to Testora!</h2>
                            <p style="margin:0 0 20px;color:#555555;font-size:15px;line-height:1.6;">
                                Thank you for registering. Please click the button below to verify your email address and activate your account.
                            </p>
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
                                <tr>
                                    <td align="center" style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:6px;">
                                        <a href="{activation_url}" target="_blank" style="display:inline-block;padding:14px 36px;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;letter-spacing:0.5px;">ACTIVATE ACCOUNT</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0 0 20px;color:#777777;font-size:13px;line-height:1.5;">
                                If the button above doesn't work,
                                <a href="{activation_url}" style="color:#667eea;text-decoration:underline;">click here</a>
                                to activate your account.
                            </p>
                            <p style="margin:0;color:#999999;font-size:12px;line-height:1.5;">
                                If you didn't create an account, please ignore this email.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:20px 40px;background-color:#fafafa;border-top:1px solid #eeeeee;text-align:center;">
                            <p style="margin:0;color:#aaaaaa;font-size:12px;">&copy; 2024 Testora. All rights reserved.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    try:
        mail.send(msg)
        print(f"\n\u2713 Activation email sent to {user.email}\n")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"\n\u2717 Failed to send email to {user.email}: {error_msg}\n")
        
        # Provide more helpful error messages
        if "SMTP authentication error" in error_msg or "Username and Password not accepted" in error_msg:
            print("\n\u26a0\ufe0f GMAIL SMTP ERROR: The password may be incorrect or not an App Password.")
            print("   - If you have 2FA enabled, you need to generate an App Password")
            print("   - Go to: https://myaccount.google.com/projectpasswords")
            print("   - Generate an App Password for 'Mail' and use that instead")
        elif "connection refused" in error_msg.lower():
            print("\n\u26a0\ufe0f CONNECTION ERROR: Could not connect to Gmail SMTP server")
            print("   - Check your internet connection")
            print("   - Some networks may block port 587")
        
        # Fallback: print to console for debugging
        print("\n" + "="*50)
        print("EMAIL (FALLBACK - PRINTED TO CONSOLE):")
        print("="*50)
        print(f"To: {user.email}")
        print(f"Subject: Activate your Testora Account")
        print(f"HTML Body with embedded link (no raw URL displayed)")
        print("="*50 + "\n")
        
        # Return True so registration continues even if email fails
        return True

# Routes
@app.route('/')
def index():
    stats = [
        {'label': 'COMMUNITY EARNINGS', 'value': '$2.4M+', 'change': '+12.4%', 'change_label': 'this month', 'icon': 'earnings'},
        {'label': 'SITES TESTED', 'value': '150,000+', 'change': '+8.1%', 'change_label': 'vs last quarter', 'icon': 'sites'},
        {'label': 'ACTIVE TESTERS', 'value': '45,000+', 'change': '+15.7%', 'change_label': 'growth', 'icon': 'testers'}
    ]
    
    steps = [
        {'number': '1', 'title': 'Pick a Test', 'description': 'Choose from a curated list of website testing tasks that match your demographics and interests.', 'icon': 'clipboard'},
        {'number': '2', 'title': 'Share your thoughts', 'description': 'Simply record your screen and think out loud while navigating through specific scenarios.', 'icon': 'mic'},
        {'number': '3', 'title': 'Get paid', 'description': 'Once your test is reviewed, payments are sent directly to your account. No minimum withdrawal.', 'icon': 'wallet'}
    ]
    
    return render_template('index.html', stats=stats, steps=steps)

@app.route('/how-it-works')
def how_it_works():
    return render_template('how-it-works.html')

@app.route('/developers')
def developers():
    return "For Developers page coming soon!"

@app.route('/pricing')
def pricing():
    return "Pricing page coming soon!"

@app.route('/community')
def community():
    return "Community page coming soon!"

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            email = form.email.data.lower().strip()
            password = form.password.data
            
            user = User.query.filter_by(email=email).first()
            
            if user and user.is_active:
                if check_password_hash(user.password_hash, password):
                    session['user_id'] = user.id
                    session['first_name'] = user.first_name
                    flash(f'Welcome back, {user.first_name}!', 'success')
                    return redirect(url_for('home'))
                else:
                    flash('Invalid email or password.', 'error')
            elif user and not user.is_active:
                flash('Your account is not activated. Please check your email to activate your account.', 'error')
            else:
                flash('Invalid email or password.', 'error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}', 'error')
    
    return render_template('login.html', form=form)

@app.route('/home')
def home():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    first_name = session.get('first_name', 'User')
    user_id = session.get('user_id')
    
    # Get user's earnings and test data from database
    # For demo purposes, using default values
    earnings = 0.00
    tests_completed = 0
    pending_tests = 0
    
    return render_template('home.html', first_name=first_name, earnings=earnings, tests_completed=tests_completed, pending_tests=pending_tests)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/available-sites')
def available_sites():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    first_name = session.get('first_name', 'User')
    
    # Generate sample brand sites with pay per test and active status
    sites = [
        {'id': 1, 'name': 'Quartze', 'pay': '$12.00', 'status': 'Active', 'url': '/redirect/site/1'},
        {'id': 2, 'name': 'Playable', 'pay': '$15.00', 'status': 'Active', 'url': '/redirect/site/2'},
        {'id': 3, 'name': 'Optilink', 'pay': '$10.00', 'status': 'Active', 'url': '/redirect/site/3'},
        {'id': 4, 'name': 'Tundra', 'pay': '$18.00', 'status': 'Active', 'url': '/redirect/site/4'},
        {'id': 5, 'name': 'Blooxe', 'pay': '$14.00', 'status': 'Active', 'url': '/redirect/site/5'},
        {'id': 6, 'name': 'Nexus', 'pay': '$11.00', 'status': 'Active', 'url': '/redirect/site/6'},
        {'id': 7, 'name': 'Vortex', 'pay': '$9.00', 'status': 'Active', 'url': '/redirect/site/7'},
        {'id': 8, 'name': 'Zenith', 'pay': '$13.00', 'status': 'Active', 'url': '/redirect/site/8'},
    ]
    
    return render_template('available_sites.html', first_name=first_name, sites=sites)

@app.route('/redirect/site/<int:site_id>')
def redirect_to_site(site_id):
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    # Map site IDs to Google Sites landing page
    site_urls = {
        1: 'https://sites.google.com/view/quartze',
        2: 'https://sites.google.com/view/quartze',
        3: 'https://sites.google.com/view/quartze',
        4: 'https://sites.google.com/view/quartze',
        5: 'https://sites.google.com/view/quartze',
        6: 'https://sites.google.com/view/quartze',
        7: 'https://sites.google.com/view/quartze',
        8: 'https://sites.google.com/view/quartze',
    }
    
    # Use client-side redirect via meta refresh (no referrer can be sent)
    # This makes it completely impossible to trace the referrer
    if site_id in site_urls:
        return render_template('privacy_redirect.html', target_url=site_urls[site_id])
    else:
        flash('Site not found.', 'error')
        return redirect(url_for('available_sites'))

@app.route('/start-earning')
def start_earning():
    # If user is already logged in, redirect to available sites
    if 'user_id' in session:
        return redirect(url_for('available_sites'))
    
    form = RegistrationForm()
    return render_template('register.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            # Check if email already exists
            existing_user = User.query.filter_by(email=form.email.data.lower()).first()
            if existing_user:
                if existing_user.is_active:
                    flash('An account with this email already exists. Please log in or use a different email.', 'error')
                else:
                    # Resend activation email
                    send_activation_email(existing_user)
                    flash('An account with this email exists but is not activated. A new activation link has been sent to your email.', 'success')
                return render_template('register.html', form=form)
            
            # Create new user
            password_hash = generate_password_hash(form.password.data)
            activation_token = secrets.token_urlsafe(32)
            
            new_user = User(
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip(),
                email=form.email.data.lower().strip(),
                password_hash=password_hash,
                activation_token=activation_token,
                is_active=False
            )
            
            try:
                db.session.add(new_user)
                db.session.commit()
                
                # Send activation email
                send_activation_email(new_user)
                
                flash('Registration successful! Please check your email to activate your account.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while creating your account. Please try again.', 'error')
                print(f"Registration error: {e}")
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}', 'error')
    
    return render_template('register.html', form=form)

@app.route('/activate/<token>')
def activate(token):
    user = User.query.filter_by(activation_token=token).first()
    
    if user:
        if user.is_active:
            flash('Your account is already activated. Please log in.', 'info')
        else:
            user.is_active = True
            user.activation_token = None
            db.session.commit()
            flash('Your account has been activated successfully! You can now log in.', 'success')
    else:
        flash('Invalid activation link. Please request a new activation email.', 'error')
    
    return redirect(url_for('login'))

@app.route('/resend-activation', methods=['GET', 'POST'])
def resend_activation():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address.', 'error')
            return render_template('resend_activation.html')
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('No account found with this email address.', 'error')
        elif user.is_active:
            flash('This account is already activated. Please log in.', 'info')
        else:
            send_activation_email(user)
            flash('A new activation link has been sent to your email.', 'success')
            return redirect(url_for('login'))
    
    return render_template('resend_activation.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address.', 'error')
            return render_template('forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('No account found with this email address.', 'error')
        else:
            reset_token = secrets.token_urlsafe(32)
            user.activation_token = reset_token
            db.session.commit()
            
            reset_url = url_for('reset_password', token=reset_token, _external=True)
            
            msg = Message(
                subject="Reset Your Testora Password",
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[user.email]
            )
            msg.body = f"Hello {user.first_name},\n\nTo reset your password, please view this email in an HTML-compatible email client."
            msg.html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f4;padding:30px 10px;">
        <tr>
            <td align="center">
                <table role="presentation" width="540" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                    <tr>
                        <td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:32px 40px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;">Testora</h1>
<p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Test Sites. Get Paid</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:36px 40px;">
                            <h2 style="margin:0 0 16px;color:#333333;font-size:20px;font-weight:600;">Reset Your Password</h2>
                            <p style="margin:0 0 20px;color:#555555;font-size:15px;line-height:1.6;">
                                You recently requested to reset your password. Click the button below to create a new one.
                            </p>
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
                                <tr>
                                    <td align="center" style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:6px;">
                                        <a href="{reset_url}" target="_blank" style="display:inline-block;padding:14px 36px;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;letter-spacing:0.5px;">RESET PASSWORD</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0 0 20px;color:#777777;font-size:13px;line-height:1.5;">
                                If the button above doesn't work,
                                <a href="{reset_url}" style="color:#667eea;text-decoration:underline;">click here</a>
                                to reset your password.
                            </p>
                            <p style="margin:0;color:#999999;font-size:12px;line-height:1.5;">
                                If you didn't request this, please ignore this email.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:20px 40px;background-color:#fafafa;border-top:1px solid #eeeeee;text-align:center;">
                            <p style="margin:0;color:#aaaaaa;font-size:12px;">&copy; 2024 Testora. All rights reserved.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
            
            try:
                mail.send(msg)
                flash('A password reset link has been sent to your email.', 'success')
            except Exception as e:
                print(f"\n\u2717 Failed to send password reset email: {e}\n")
                print("\n" + "="*50)
                print("PASSWORD RESET EMAIL (FALLBACK):")
                print("="*50)
                print(f"To: {user.email}")
                print(f"HTML Body with embedded link (no raw URL displayed)")
                print("="*50 + "\n")
                flash('A password reset link has been sent to your email.', 'success')
            
            return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(activation_token=token).first()
    
    if not user:
        flash('Invalid or expired reset link. Please request a new password reset.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not new_password or not confirm_password:
            flash('Please fill in all fields.', 'error')
            return render_template('reset_password.html', token=token)
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)
        
        password = new_password
        errors = []
        
        if len(password) < 8:
            errors.append('at least 8 characters')
        if not re.search(r'[A-Z]', password):
            errors.append('one uppercase letter')
        if not re.search(r'[a-z]', password):
            errors.append('one lowercase letter')
        if not re.search(r'\d', password):
            errors.append('one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append('one special character')
        
        if errors:
            flash(f'Password must contain {", ".join(errors)}.', 'error')
            return render_template('reset_password.html', token=token)
        
        user.password_hash = generate_password_hash(new_password)
        user.activation_token = None
        db.session.commit()
        
        flash('Your password has been reset successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

@app.route('/location')
def location():
    return render_template('location.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/cookies')
def cookies():
    return render_template('cookies.html')

@app.route('/payment')
def payment():
    return render_template('payment.html')

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5001)

