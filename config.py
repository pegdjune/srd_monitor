import os
from dotenv import load_dotenv

# Charger le fichier .env
# load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'srd_data', '.env'))
load_dotenv()  # Charger les variables d'environnement depuis le fichier .env

GMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email':  os.getenv('GMAIL_SENDER_EMAIL'), # 'djunehawks@gmail.com',
    'app_password': os.getenv('GMAIL_APP_PASSWORD') # 'ceiw xvra isqx qiql'  # Mot de passe d'application
}

print(GMAIL_CONFIG)
# Liste des destinataires
RECIPIENTS = ['pegdjune19@gmail.com']  # 'starkdane06@gmail.com'

# Seuils de variation pour l'alerte
VARATION_THRESHOLD = 3.0  # Seuil de variation en % (positif et négatif)

# Configuration des chemins
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'srd_data')
os.makedirs(DATA_DIR, exist_ok=True)  # Création du dossier si inexistant