#!/usr/bin/python3
import smtplib
from config import BREVO_CONFIG
from config import GMAIL_CONFIG
from dotenv import load_dotenv
import os

load_dotenv()  # Charger les variables d'environnement depuis le fichier .env

def test_smtp_connection():
    """Test de connexion SMTP à Brevo"""
    try:
        print("Test de connexion SMTP Brevo...")
        print(f"Server: {BREVO_CONFIG['smtp_server']}:{BREVO_CONFIG['smtp_port']}")
        print(f"Login: {BREVO_CONFIG['sender_email']}")
        print(f"API Key: {BREVO_CONFIG['api_key'][:10]}...")  # Affiche seulement les 10 premiers caractères
        
        # Connexion au serveur
        with smtplib.SMTP(BREVO_CONFIG['smtp_server'], BREVO_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(BREVO_CONFIG['sender_email'], BREVO_CONFIG['smtpkey'])
            print("✅ Connexion SMTP réussie!")
            
        return True
        
    except Exception as e:
        print(f"❌ Erreur SMTP: {e}")
        return False


def test_smtp_connectiongmail():
    """Test de connexion SMTP à Gmail."""

    try:
        print("Test de connexion SMTP Gmail...")

        # Connexion au serveur
        with smtplib.SMTP(GMAIL_CONFIG['smtp_server'], GMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(GMAIL_CONFIG['sender_email'], GMAIL_CONFIG['app_password'])  # Utilisation du mot de passe d'application
            print("✅ Connexion SMTP réussie avec Gmail!")
            
        return True
        
    except Exception as e:
        print(f"❌ Erreur SMTP: {e}")
        return False


if __name__ == "__main__":
    test_smtp_connectiongmail()