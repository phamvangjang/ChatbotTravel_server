from flask import Blueprint, request, jsonify
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
import jwt
from functools import wraps
from app import db, mail
from app.models import Users, OTP
import os
from dotenv import load_dotenv
from flask_restx import Api, Resource, fields, Namespace
import random
import string

load_dotenv()

# Create namespace for auth
auth_ns = Namespace('auth', description='Authentication operations')

# Define models for Swagger documentation
register_model = auth_ns.model('Register', {
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password'),
    'full_name': fields.String(required=True, description='User full name'),
    'language_preference': fields.String(description='User language preference', default='en')
})

verify_otp_model = auth_ns.model('VerifyOTP', {
    'email': fields.String(required=True, description='User email'),
    'otp_code': fields.String(required=True, description='OTP code')
})

login_model = auth_ns.model('Login', {
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password')
})

forgot_password_model = auth_ns.model('ForgotPassword', {
    'email': fields.String(required=True, description='User email')
})

verify_reset_otp_model = auth_ns.model('VerifyResetOTP', {
    'email': fields.String(required=True, description='User email'),
    'otp_code': fields.String(required=True, description='OTP code')
})

reset_password_model = auth_ns.model('ResetPassword', {
    'email': fields.String(required=True, description='User email'),
    'otp_code': fields.String(required=True, description='OTP code'),
    'password': fields.String(required=True, description='New password')
})

user_model = auth_ns.model('User', {
    'id': fields.Integer(description='User ID'),
    'email': fields.String(description='User email'),
    'full_name': fields.String(description='User full name'),
    'language_preference': fields.String(description='User language preference'),
    'is_verified': fields.Boolean(description='Email verification status')
})

login_response = auth_ns.model('LoginResponse', {
    'token': fields.String(description='JWT token'),
    'user': fields.Nested(user_model)
})

serializer = URLSafeTimedSerializer(os.getenv('SECRET_KEY'))

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp_code, purpose):
    subject = 'Email Verification' if purpose == 'register' else 'Password Reset'
    msg = Message(subject,
                  sender=os.getenv('MAIL_DEFAULT_SENDER'),
                  recipients=[email])
    msg.body = f'''Your verification code is: {otp_code}

This code will expire in 5 minutes.

If you did not request this code, please ignore this email.
'''
    mail.send(msg)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return {'message': 'Token is missing!'}, 401
        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=["HS256"])
            current_user = Users.query.get(data['user_id'])
        except:
            return {'message': 'Token is invalid!'}, 401
        return f(current_user, *args, **kwargs)
    return decorated

@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model)
    @auth_ns.response(201, 'Registration initiated. Please check your email for OTP verification.')
    @auth_ns.response(400, 'Missing required fields or email already registered')
    def post(self):
        data = request.get_json()
        
        if not all(k in data for k in ('email', 'password', 'full_name')):
            return {'message': 'Missing required fields'}, 400
        
        if Users.query.filter_by(email=data['email']).first():
            return {'message': 'Email already registered'}, 400
        
        # Generate OTP
        otp_code = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        # Save OTP
        otp = OTP(
            email=data['email'],
            otp_code=otp_code,
            purpose='register',
            expires_at=expires_at
        )
        db.session.add(otp)
        
        # Save user with unverified status
        hashed_password = generate_password_hash(data['password'])
        new_user = Users(
            email=data['email'],
            password_hash=hashed_password,
            full_name=data['full_name'],
            language_preference=data.get('language_preference', 'en'),
            is_verified=False
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Send OTP email
        send_otp_email(data['email'], otp_code, 'register')
        
        return {'message': 'Registration initiated. Please check your email for OTP verification.'}, 201

@auth_ns.route('/verify-otp')
class VerifyOTP(Resource):
    @auth_ns.expect(verify_otp_model)
    @auth_ns.response(200, 'Email verified successfully')
    @auth_ns.response(400, 'Invalid or expired OTP')
    def post(self):
        data = request.get_json()
        
        if not all(k in data for k in ('email', 'otp_code')):
            return {'message': 'Missing email or OTP code'}, 400
        
        otp = OTP.query.filter_by(
            email=data['email'],
            otp_code=data['otp_code'],
            purpose='register',
            is_used=False
        ).first()
        
        if not otp or otp.expires_at < datetime.utcnow():
            return {'message': 'Invalid or expired OTP'}, 400
        
        # Mark OTP as used
        otp.is_used = True
        
        # Mark user as verified
        user = Users.query.filter_by(email=data['email']).first()
        user.is_verified = True
        
        # Delete all OTP records for this email and purpose
        OTP.query.filter_by(
            email=data['email'],
            purpose='register'
        ).delete()
        
        db.session.commit()
        
        return {'message': 'Email verified successfully'}

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.response(200, 'Login successful', login_response)
    @auth_ns.response(400, 'Missing email or password')
    @auth_ns.response(401, 'Invalid email or password or email not verified')
    def post(self):
        data = request.get_json()
        
        if not all(k in data for k in ('email', 'password')):
            return {'message': 'Missing email or password'}, 400
        
        user = Users.query.filter_by(email=data['email']).first()
        
        if not user or not check_password_hash(user.password_hash, data['password']):
            return {'message': 'Invalid email or password'}, 401
            
        if not user.is_verified:
            return {'message': 'Please verify your email first'}, 401
        
        token = jwt.encode({
            'user_id': user.user_id,
            'exp': datetime.utcnow() + timedelta(days=1)
        }, os.getenv('SECRET_KEY'))
        
        return {
            'token': token,
            'user': {
                'id': user.user_id,
                'email': user.email,
                'full_name': user.full_name,
                'language_preference': user.language_preference,
                'is_verified': user.is_verified
            }
        }

@auth_ns.route('/forgot-password')
class ForgotPassword(Resource):
    @auth_ns.expect(forgot_password_model)
    @auth_ns.response(200, 'Password reset OTP sent')
    @auth_ns.response(404, 'Email not found')
    def post(self):
        data = request.get_json()
        
        if 'email' not in data:
            return {'message': 'Email is required'}, 400
        
        user = Users.query.filter_by(email=data['email']).first()
        
        if not user:
            return {'message': 'Email not found'}, 404
        
        # Generate OTP
        otp_code = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        # Save OTP
        otp = OTP(
            email=data['email'],
            otp_code=otp_code,
            purpose='reset_password',
            expires_at=expires_at
        )
        db.session.add(otp)
        db.session.commit()
        
        # Send OTP email
        send_otp_email(data['email'], otp_code, 'reset_password')
        
        return {'message': 'Password reset OTP sent'}

@auth_ns.route('/verify-reset-otp')
class VerifyResetOTP(Resource):
    @auth_ns.expect(verify_reset_otp_model)
    @auth_ns.response(200, 'OTP verified successfully')
    @auth_ns.response(400, 'Invalid or expired OTP')
    def post(self):
        data = request.get_json()
        
        if not all(k in data for k in ('email', 'otp_code')):
            return {'message': 'Missing email or OTP code'}, 400
        
        otp = OTP.query.filter_by(
            email=data['email'],
            otp_code=data['otp_code'],
            purpose='reset_password',
            is_used=False
        ).first()
        
        if not otp or otp.expires_at < datetime.utcnow():
            return {'message': 'Invalid or expired OTP'}, 400
        
        # Mark OTP as used
        otp.is_used = True
        db.session.commit()
        
        return {'message': 'OTP verified successfully'}

@auth_ns.route('/reset-password')
class ResetPassword(Resource):
    @auth_ns.expect(reset_password_model)
    @auth_ns.response(200, 'Password has been reset successfully')
    @auth_ns.response(400, 'Invalid request or OTP')
    def post(self):
        data = request.get_json()
        
        if not all(k in data for k in ('email', 'otp_code', 'password')):
            return {'message': 'Missing required fields'}, 400
        
        # Verify that OTP was used
        otp = OTP.query.filter_by(
            email=data['email'],
            otp_code=data['otp_code'],
            purpose='reset_password',
            is_used=True
        ).first()
        
        if not otp:
            return {'message': 'Please verify OTP first'}, 400
        
        # Update password
        user = Users.query.filter_by(email=data['email']).first()
        user.password_hash = generate_password_hash(data['password'])
        
        # Delete all OTP records for this email and purpose
        OTP.query.filter_by(
            email=data['email'],
            purpose='reset_password'
        ).delete()
        
        db.session.commit()
        
        return {'message': 'Password has been reset successfully'} 