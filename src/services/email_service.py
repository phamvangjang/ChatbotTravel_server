from flask_mail import Message
from src.config.config import Config
from src import mail

def send_otp_email(email, otp_code, purpose):
    subject = 'Email Verification' if purpose == 'register' else 'Password Reset'
    msg = Message(subject,
                  sender=Config.MAIL_DEFAULT_SENDER,
                  recipients=[email])
    msg.body = f'''Your verification code is: {otp_code}

This code will expire in 5 minutes.

If you did not request this code, please ignore this email.
'''
    mail.send(msg) 