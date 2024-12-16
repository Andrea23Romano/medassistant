import hashlib  # Add this import

def hash_password(password):
    # Create a SHA-256 hash of the password
    return hashlib.sha256(password.encode()).hexdigest()

