import os
import jwt
import random
import string
import resend
from functools import wraps
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from rag_pipeline import YouTubeRAGEngine
from models import db, Video, ChatMessage, User
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_super_secret_jwt_key_123")

# Resend API Key Configuration
resend.api_key = os.getenv("RESEND_API_KEY", "re_AbdAtEjh_P1KohQxeDwdbe84887oNpJkV")

# Database URL Handling
db_url = os.getenv('DATABASE_URL', 'mysql+pymysql://root:Mursleen%40999@localhost:3306/youtube_rag_db')

# Clean any ssl-mode parameters if passed from URL
if "?ssl-mode=" in db_url or "&ssl-mode=" in db_url:
    db_url = db_url.split("?ssl-mode=")[0].split("&ssl-mode=")[0]

if db_url.startswith("mysql://"):
    db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Force SSL connection settings for Aiven Cloud MySQL
if "aivencloud.com" in db_url:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {
            "ssl": {"ssl_mode": "REQUIRED"}
        }
    }

# Temporary in-memory OTP storage {email: otp_code}
otp_store = {}

db.init_app(app)
rag_engine = YouTubeRAGEngine()

with app.app_context():
    db.create_all()

# Root Health Route (Prevents 404 on base URL)
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "Backend is live and running!"}), 200

# JWT Authentication Decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        try:
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': 'Invalid User!'}), 401
        except Exception as e:
            return jsonify({'error': 'Token is invalid or expired!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# 1. Signup Endpoint (Fixed Duplicate Registration Check)
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    # Strict check: Block duplicate email or username with clear 400 error
    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        if existing_user.email == email:
            return jsonify({"error": "Email is already registered. Please log in or reset password."}), 400
        return jsonify({"error": "Username is already taken. Choose another one."}), 400

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully!"}), 201

# 2. Login Endpoint
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = jwt.encode({"user_id": user.id}, SECRET_KEY, algorithm="HS256")
    return jsonify({
        "message": "Login successful",
        "token": token,
        "username": user.username
    }), 200

# 3. Forgot Password - Send OTP via Resend HTTP API
@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    try:
        data = request.get_json() or {}
        email = data.get("email")

        if not email:
            return jsonify({"error": "Email is required"}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"error": "No account found with this email!"}), 404

        # Generate random 6-digit OTP
        otp = ''.join(random.choices(string.digits, k=6))
        otp_store[email] = otp

        # Send Email via Resend API
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": email,
            "subject": "Your Password Reset Code - RAG AI",
            "html": f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #0f172a; color: #ffffff; border-radius: 8px;">
                    <h2 style="color: #38bdf8;">Password Reset Request</h2>
                    <p>Hello <strong>{user.username}</strong>,</p>
                    <p>Your 6-digit verification code to reset your password is:</p>
                    <div style="background-color: #1e293b; font-size: 24px; font-weight: bold; letter-spacing: 4px; padding: 12px 20px; width: fit-content; border-radius: 6px; color: #38bdf8;">
                        {otp}
                    </div>
                    <p style="margin-top: 20px; font-size: 12px; color: #94a3b8;">If you did not request this, please ignore this email.</p>
                </div>
            """
        })

        return jsonify({"message": "OTP code sent to your email!"}), 200

    except Exception as e:
        print("RESEND API MAIL ERROR:", str(e))
        return jsonify({"error": f"Failed to send OTP email: {str(e)}"}), 500

# 4. Reset Password - Verify OTP & Update Password
@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email")
    user_otp = data.get("otp")
    new_password = data.get("password")

    if not email or not user_otp or not new_password:
        return jsonify({"error": "All fields are required!"}), 400

    # Verify OTP Code
    if email not in otp_store or otp_store[email] != str(user_otp):
        return jsonify({"error": "Invalid or expired OTP code!"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found!"}), 404

    # Update Password
    user.set_password(new_password)
    db.session.commit()

    # Clear used OTP
    del otp_store[email]

    return jsonify({"message": "Password updated successfully! You can now log in."}), 200

# 5. User Specific Videos List
@app.route("/api/videos", methods=["GET"])
@token_required
def get_user_videos(current_user):
    try:
        videos = Video.query.filter_by(user_id=current_user.id).order_by(Video.created_at.desc()).all()
        video_list = [{"id": v.id, "video_id": v.video_id, "url": v.url} for v in videos]
        return jsonify({"videos": video_list}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 6. User Specific Chat History
@app.route("/api/history/<video_id>", methods=["GET"])
@token_required
def get_chat_history(current_user, video_id):
    try:
        messages = ChatMessage.query.filter_by(user_id=current_user.id, video_id=video_id).order_by(ChatMessage.timestamp.asc()).all()
        history = [{"sender": msg.sender, "text": msg.message} for msg in messages]
        return jsonify({"history": history}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 7. Process Video Endpoint
@app.route("/api/process-video", methods=["POST"])
@token_required
def process_video(current_user):
    data = request.get_json()
    video_url = data.get("video_url")
    if not video_url:
        return jsonify({"error": "video_url is required"}), 400

    try:
        rag_engine.process_video(video_url)
        video_id = rag_engine._extract_video_id(video_url)

        existing_video = Video.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        if not existing_video:
            new_video = Video(user_id=current_user.id, video_id=video_id, url=video_url)
            db.session.add(new_video)
            db.session.commit()

        return jsonify({"message": "Video indexed!", "video_id": video_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 8. Stream Chat Endpoint
@app.route("/api/chat-stream", methods=["POST"])
@token_required
def chat_stream(current_user):
    data = request.get_json()
    question = data.get("question")
    video_id = data.get("video_id")

    if not question or not video_id:
        return jsonify({"error": "question and video_id are required"}), 400

    def generate():
        full_answer = ""
        try:
            for chunk in rag_engine.stream_answer(video_id, question):
                full_answer += chunk
                yield chunk

            with app.app_context():
                user_msg = ChatMessage(user_id=current_user.id, video_id=video_id, sender='user', message=question)
                bot_msg = ChatMessage(user_id=current_user.id, video_id=video_id, sender='bot', message=full_answer)
                db.session.add(user_msg)
                db.session.add(bot_msg)
                db.session.commit()
        except Exception as e:
            yield f" [Error: {str(e)}]"

    return Response(stream_with_context(generate()), content_type='text/plain; charset=utf-8')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)