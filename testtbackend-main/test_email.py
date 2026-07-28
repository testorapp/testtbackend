"""
Test script to verify email sending functionality
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Print email configuration (mask password for security)
print("=" * 50)
print("EMAIL CONFIGURATION TEST")
print("=" * 50)
print(f"MAIL_SERVER: {os.environ.get('MAIL_SERVER', 'smtp.gmail.com')}")
print(f"MAIL_PORT: {os.environ.get('MAIL_PORT', 587)}")
print(f"MAIL_USERNAME: {os.environ.get('MAIL_USERNAME', 'testora.inc@gmail.com')}")

print(f"MAIL_PASSWORD: {'*' * len(os.environ.get('MAIL_PASSWORD', ''))}")
print(f"MAIL_USE_TLS: {os.environ.get('MAIL_USE_TLS', True)}")
print("=" * 50)

# Test Flask-Mail configuration
from flask import Flask
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'testora.inc@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'testora.inc@gmail.com')

# Basic sanity check so failures are clear
if not app.config['MAIL_USERNAME']:
    raise RuntimeError('MAIL_USERNAME is missing')
if not app.config['MAIL_PASSWORD']:
    raise RuntimeError('MAIL_PASSWORD is missing (set a Gmail App Password in your environment)')

mail = Mail(app)


# Test sending an email
with app.app_context():
    try:
        msg = Message(
            subject="Test Email from Testora",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[app.config['MAIL_USERNAME']]  # Send to yourself for testing
        )
        msg.body = "This is a test email to verify the forgot password email function is working!"
        
        mail.send(msg)
        print("\n✓ SUCCESS: Email sent successfully!")
        print(f"   Email sent to: {app.config['MAIL_USERNAME']}")
    except Exception as e:
        error_msg = str(e)
        print(f"\n✗ FAILED: {error_msg}")
        print("\nPossible solutions:")
        print("1. Make sure the App Password is correct (16 characters)")
        print("2. Check that 2-Step Verification is enabled on your Google account")
        print("3. Verify the App Password was generated for 'Mail'")
        
        # Provide more helpful error messages
        if "SMTP authentication error" in error_msg or "Username and Password not accepted" in error_msg:
            print("\n⚠️ GMAIL SMTP ERROR: The password may be incorrect or not an App Password.")
            print("   - If you have 2FA enabled, you need to generate an App Password")
            print("   - Go to: https://myaccount.google.com/projectpasswords")
            print("   - Generate an App Password for 'Mail' and use that instead")
        elif "connection refused" in error_msg.lower():
            print("\n⚠️ CONNECTION ERROR: Could not connect to Gmail SMTP server")
            print("   - Check your internet connection")
            print("   - Some networks may block port 587")
