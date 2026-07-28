"""Testora Backend - Authentication Routes (Register, Login, Activate, Password Reset)"""
import secrets
import re
from datetime import datetime
from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from models import User, db
from extensions import mail
from routes import auth_bp


def send_email(subject, recipient, body, html_body=None):
    """Send email via Flask-Mail with console fallback"""
    try:
        msg = Message(
            subject=subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[recipient]
        )
        msg.body = body
        if html_body:
            msg.html = html_body
        mail.send(msg)
        print(f"\n\u2713 Email sent to {recipient}\n")
        return True
    except Exception as e:
        print(f"\n\u2717 Failed to send email to {recipient}: {e}\n")
        print("\n" + "=" * 50)
        print(f"EMAIL FALLBACK - To: {recipient}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        if html_body:
            print(f"HTML Body:\n{html_body}")
        print("=" * 50 + "\n")
        return True  # Continue even if email fails


def validate_password_strength(password):
    """Validate password meets requirements"""
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
    return errors


def _build_activation_html(activation_url, button_text="ACTIVATE ACCOUNT"):
    """Build HTML email content for activation links"""
    return f"""<!DOCTYPE html>
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
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:32px 40px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:0.5px;">Testora</h1>
                            <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Test Sites. Get Paid</p>
                        </td>
                    </tr>
                    <!-- Body -->
                    <tr>
                        <td style="padding:36px 40px;">
                            <h2 style="margin:0 0 16px;color:#333333;font-size:20px;font-weight:600;">Welcome to Testora!</h2>
                            <p style="margin:0 0 20px;color:#555555;font-size:15px;line-height:1.6;">
                                Thank you for signing up. Please click the button below to verify your email address and activate your account.
                            </p>
                            <!-- Button -->
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
                                <tr>
                                    <td align="center" style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:6px;">
                                        <a href="{activation_url}" target="_blank" style="display:inline-block;padding:14px 36px;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;letter-spacing:0.5px;">{button_text}</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0 0 20px;color:#777777;font-size:13px;line-height:1.5;">
                                If the button above doesn't work,
                                <a href="{activation_url}" style="color:#667eea;text-decoration:underline;">click here</a>
                                to activate your account.
                            </p>
                            <p style="margin:0;color:#999999;font-size:12px;line-height:1.5;">
                                This link will expire after you use it. If you didn't create an account, please ignore this email.
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
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


def _build_reset_html(reset_url):
    """Build HTML email content for password reset links"""
    return f"""<!DOCTYPE html>
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
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:32px 40px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:0.5px;">Testora</h1>
                            <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Test Sites. Get Paid</p>
                        </td>
                    </tr>
                    <!-- Body -->
                    <tr>
                        <td style="padding:36px 40px;">
                            <h2 style="margin:0 0 16px;color:#333333;font-size:20px;font-weight:600;">Reset Your Password</h2>
                            <p style="margin:0 0 20px;color:#555555;font-size:15px;line-height:1.6;">
                                You recently requested to reset your password. Click the button below to create a new one.
                            </p>
                            <!-- Button -->
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
                                If you didn't request a password reset, please ignore this email.
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
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


def _build_welcome_back_html(activation_url):
    """Build HTML email content for re-sending activation to existing inactive user"""
    return f"""<!DOCTYPE html>
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
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:32px 40px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:0.5px;">Testora</h1>
                            <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Test Sites. Get Paid</p>
                        </td>
                    </tr>
                    <!-- Body -->
                    <tr>
                        <td style="padding:36px 40px;">
                            <h2 style="margin:0 0 16px;color:#333333;font-size:20px;font-weight:600;">Welcome Back!</h2>
                            <p style="margin:0 0 20px;color:#555555;font-size:15px;line-height:1.6;">
                                You already have an account with us that hasn't been activated yet. Click the button below to verify your email and activate it.
                            </p>
                            <!-- Button -->
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
                                If you didn't request this, please ignore this email.
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
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


def _build_reset_confirmation_html(login_url):
    """Build HTML email content for password reset success confirmation"""
    return f"""<!DOCTYPE html>
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
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:32px 40px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:0.5px;">Testora</h1>
                            <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Test Sites. Get Paid</p>
                        </td>
                    </tr>
                    <!-- Body -->
                    <tr>
                        <td style="padding:36px 40px;">
                            <h2 style="margin:0 0 16px;color:#333333;font-size:20px;font-weight:600;">Password Reset Successful</h2>
                            <p style="margin:0 0 20px;color:#555555;font-size:15px;line-height:1.6;">
                                Your password has been successfully reset. You can now log in to your account using your new password.
                            </p>
                            <!-- Button -->
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
                                <tr>
                                    <td align="center" style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:6px;">
                                        <a href="{login_url}" target="_blank" style="display:inline-block;padding:14px 36px;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;letter-spacing:0.5px;">LOG IN TO TESTORA</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0 0 20px;color:#777777;font-size:13px;line-height:1.5;">
                                If the button above doesn't work,
                                <a href="{login_url}" style="color:#667eea;text-decoration:underline;">click here</a>
                                to log in.
                            </p>
                            <p style="margin:0;color:#999999;font-size:12px;line-height:1.5;">
                                If you didn't make this change, please contact support immediately.
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
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


# ─── REGISTER ───────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'message': 'Invalid request body.'}), 400

    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    confirm_password = data.get('confirm_password') or ''

    # Validation
    if not first_name or len(first_name) < 2 or len(first_name) > 50:
        return jsonify({'success': False, 'message': 'First name must be 2-50 characters.'}), 400
    if not re.match(r"^[a-zA-Z\s\-']+$", first_name):
        return jsonify({'success': False, 'message': 'First name contains invalid characters.'}), 400
    if not last_name or len(last_name) < 2 or len(last_name) > 50:
        return jsonify({'success': False, 'message': 'Last name must be 2-50 characters.'}), 400
    if not re.match(r"^[a-zA-Z\s\-']+$", last_name):
        return jsonify({'success': False, 'message': 'Last name contains invalid characters.'}), 400
    if not email or '@' not in email:
        return jsonify({'success': False, 'message': 'Valid email is required.'}), 400

    pw_errors = validate_password_strength(password)
    if pw_errors:
        return jsonify({'success': False, 'message': f'Password must contain {", ".join(pw_errors)}.'}), 400

    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400

    # Check existing user
    existing = User.query.filter_by(email=email).first()
    if existing:
        if existing.is_active:
            return jsonify({'success': False, 'message': 'An account with this email already exists.'}), 409
        else:
            # Resend activation
            activation_token = secrets.token_urlsafe(32)
            existing.activation_token = activation_token
            db.session.commit()
            frontend_url = current_app.config['FRONTEND_URL']
            activation_url = f"{frontend_url}/activate.html?token={activation_token}"
            send_email(
                subject="Activate your Testora Account",
                recipient=email,
                body="Welcome back! Your account needs activation. To activate, please view this email in an HTML-compatible email client.",
                html_body=_build_welcome_back_html(activation_url)
            )
            return jsonify({'success': True, 'message': 'A new activation link has been sent to your email.'}), 200

    # Create user
    password_hash = generate_password_hash(password)
    activation_token = secrets.token_urlsafe(32)

    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=password_hash,
        activation_token=activation_token,
        is_active=False
    )

    try:
        db.session.add(new_user)
        db.session.commit()

        frontend_url = current_app.config['FRONTEND_URL']
        activation_url = f"{frontend_url}/activate.html?token={activation_token}"
        send_email(
            subject="Activate your Testora Account",
            recipient=email,
            body="Welcome to Testora! To activate your account, please view this email in an HTML-compatible email client and click the activation button.",
            html_body=_build_activation_html(activation_url)
        )

        return jsonify({'success': True, 'message': 'Registration successful! Check your email to activate.'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred during registration.'}), 500


# ─── LOGIN ──────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'message': 'Invalid request body.'}), 400

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401

    if not user.is_active:
        return jsonify({'success': False, 'message': 'Account not activated. Check your email.'}), 403

    if not check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401

    # Generate JWT-like token (simple session token for now)
    token = secrets.token_urlsafe(48)

    return jsonify({
        'success': True,
        'token': token,
        'user': user.to_dict()
    }), 200


# ─── ACTIVATE ───────────────────────────────────────────────
@auth_bp.route('/activate/<token>', methods=['GET'])
def activate(token):
    user = User.query.filter_by(activation_token=token).first()

    if not user:
        return jsonify({'success': False, 'message': 'Invalid or expired activation link.'}), 400

    if user.is_active:
        return jsonify({'success': True, 'message': 'Account already activated. Please log in.'}), 200

    user.is_active = True
    user.activation_token = None
    db.session.commit()

    return jsonify({'success': True, 'message': 'Account activated successfully! Please log in.'}), 200


# ─── RESEND ACTIVATION ──────────────────────────────────────
@auth_bp.route('/resend-activation', methods=['POST'])
def resend_activation():
    data = request.get_json(silent=True)
    email = (data.get('email') or '').strip().lower() if data else ''

    if not email:
        return jsonify({'success': False, 'message': 'Email is required.'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'success': False, 'message': 'No account found with this email.'}), 404
    if user.is_active:
        return jsonify({'success': False, 'message': 'Account already activated.'}), 400

    activation_token = secrets.token_urlsafe(32)
    user.activation_token = activation_token
    db.session.commit()

    frontend_url = current_app.config['FRONTEND_URL']
    activation_url = f"{frontend_url}/activate.html?token={activation_token}"
    send_email(
        subject="Activate your Testora Account",
        recipient=email,
        body="To activate your account, please view this email in an HTML-compatible email client and click the activation button.",
        html_body=_build_activation_html(activation_url)
    )

    return jsonify({'success': True, 'message': 'Activation link resent.'}), 200


# ─── FORGOT PASSWORD ────────────────────────────────────────
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json(silent=True)
    email = (data.get('email') or '').strip().lower() if data else ''

    if not email:
        return jsonify({'success': False, 'message': 'Email is required.'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        # Don't reveal whether email exists
        return jsonify({'success': True, 'message': 'If the email exists, a reset link has been sent.'}), 200

    reset_token = secrets.token_urlsafe(32)
    user.activation_token = reset_token
    db.session.commit()

    frontend_url = current_app.config['FRONTEND_URL']
    reset_url = f"{frontend_url}/reset-password.html?token={reset_token}"
    send_email(
        subject="Reset Your Testora Password",
        recipient=email,
        body=f"Hello {user.first_name},\n\nTo reset your password, please view this email in an HTML-compatible email client and click the reset password button.",
        html_body=_build_reset_html(reset_url)
    )

    return jsonify({'success': True, 'message': 'If the email exists, a reset link has been sent.'}), 200


# ─── RESET PASSWORD ─────────────────────────────────────────
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'message': 'Invalid request body.'}), 400

    token = data.get('token', '')
    new_password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not token:
        return jsonify({'success': False, 'message': 'Reset token is required.'}), 400

    user = User.query.filter_by(activation_token=token).first()

    if not user:
        return jsonify({'success': False, 'message': 'Invalid or expired reset link.'}), 400

    if not new_password or not confirm_password:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    if new_password != confirm_password:
        return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400

    pw_errors = validate_password_strength(new_password)
    if pw_errors:
        return jsonify({'success': False, 'message': f'Password must contain {", ".join(pw_errors)}.'}), 400

    user.password_hash = generate_password_hash(new_password)
    user.activation_token = None
    first_name = user.first_name
    user_email = user.email
    db.session.commit()

    # Send password reset confirmation email
    frontend_url = current_app.config['FRONTEND_URL']
    login_url = f"{frontend_url}/login.html"
    send_email(
        subject="Your Testora Password Has Been Reset",
        recipient=user_email,
        body=f"Hello {first_name},\n\nYour password has been successfully reset. To log in, please view this email in an HTML-compatible email client and click the login button.",
        html_body=_build_reset_confirmation_html(login_url)
    )

    return jsonify({'success': True, 'message': 'Password reset successfully! Please log in.'}), 200

