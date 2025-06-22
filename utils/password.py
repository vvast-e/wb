from passlib.context import CryptContext
from cryptography.fernet import Fernet, InvalidToken
from config import settings
from typing import Dict
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def encrypt_api_dict(api_dict: Dict[str, str]) -> Dict[str, str]:
    """Шифрует все API-ключи в словаре"""
    return {brand: cipher_suite.encrypt(api_key.encode()).decode()
            for brand, api_key in api_dict.items()}



def decrypt_api_dict(encrypted_dict: Dict[str, str]) -> Dict[str, str]:
    """Расшифровывает все API-ключи в словаре с обработкой ошибок"""
    decrypted = {}
    for brand, api_key in encrypted_dict.items():
        try:
            if not api_key:
                continue
            decrypted[brand] = cipher_suite.decrypt(api_key.encode()).decode()
        except InvalidToken:
            logger.warning(f"Failed to decrypt API key for brand {brand}")
            decrypted[brand] = ""
        except Exception as e:
            logger.error(f"Unexpected error decrypting key for {brand}: {str(e)}")
            decrypted[brand] = ""
    return decrypted

def encrypt_api_key(api_key: str) -> str:
    if not api_key:
        return ""
    return cipher_suite.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    if not encrypted_key:
        return ""
    return cipher_suite.decrypt(encrypted_key.encode()).decode()