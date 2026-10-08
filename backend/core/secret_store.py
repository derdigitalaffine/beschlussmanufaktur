"""Runtime key material is separate from database/backups; empty disables features."""
import os
from cryptography.fernet import Fernet,InvalidToken
from django.core.exceptions import ValidationError

def cipher():
    value=os.environ.get('DATA_ENCRYPTION_KEY','')
    try:return Fernet(value.encode())
    except (ValueError,TypeError):raise ValidationError('DATA_ENCRYPTION_KEY fehlt oder ist ungültig; verschlüsselte Funktionen sind gesperrt.')
def encrypt(value):return cipher().encrypt(value.encode()).decode()
def decrypt(value):
    try:return cipher().decrypt(value.encode()).decode()
    except InvalidToken:raise ValidationError('Geschützter Wert nicht entschlüsselbar.')
