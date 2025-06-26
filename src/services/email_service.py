from flask_mail import Message
from src.config.config import Config
from src import mail

def send_otp_email(email, otp_code, purpose):
    subject = 'Email Verification' if purpose == 'register' else 'Password Reset'
    msg = Message(subject,
                  sender=Config.MAIL_DEFAULT_SENDER,
                  recipients=[email])
    # HTML template cho email OTP
    msg.html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto; border: 1px solid #eee; border-radius: 8px; box-shadow: 0 2px 8px #f0f0f0; padding: 32px 24px; background: #fff;">
        <h2 style="color: #2d8cf0; text-align: center;">{subject}</h2>
        <p style="font-size: 16px; color: #333; text-align: center;">Your verification code is:</p>
        <div style="font-size: 32px; font-weight: bold; color: #2d8cf0; text-align: center; letter-spacing: 8px; margin: 24px 0;">{otp_code}</div>
        <p style="font-size: 15px; color: #555; text-align: center;">This code will expire in <b>5 minutes</b>.</p>
        <hr style="margin: 32px 0; border: none; border-top: 1px solid #eee;">
        <p style="font-size: 13px; color: #999; text-align: center;">If you did not request this code, please ignore this email.</p>
        <p style="font-size: 13px; color: #bbb; text-align: center; margin-top: 16px;">&copy; {subject} - ScapeData</p>
    </div>
    '''
    msg.body = f"Your verification code is: {otp_code}\n\nThis code will expire in 5 minutes.\n\nIf you did not request this code, please ignore this email."
    mail.send(msg) 