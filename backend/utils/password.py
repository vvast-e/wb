from passlib.context import CryptContext
from cryptography.fernet import Fernet
from backend.config import settings

# Для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Для шифрования API-ключа
cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def encrypt_api_key(api_key: str) -> str:
    """Шифрует API-ключ для хранения в БД"""
    return cipher_suite.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Расшифровывает API-ключ для использования"""
    return cipher_suite.decrypt(encrypted_key.encode()).decode()