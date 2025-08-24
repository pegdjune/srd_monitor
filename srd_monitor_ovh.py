#!/usr/bin/python3
import sys
import os
import csv
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup

# Ajout du chemin du projet
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import  RECIPIENTS, DATA_DIR, GMAIL_CONFIG
except ImportError:
    print("Erreur: Fichier config.py introuvable")
    sys.exit(1)

def log_message(message):
    """Journalisation des messages"""
    log_file = os.path.join(DATA_DIR, 'srd_monitor.log')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{timestamp} - {message}\n"
    
    print(log_entry.strip())
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def fetch_srd_data():
    """Extraction des données du SRD depuis Boursier.com en utilisant les filtres alphabétiques"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'https://www.boursier.com/',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        log_message("Récupération des données du SRD en utilisant les filtres alphabétiques...")
        base_url = 'https://www.boursier.com/actions/paris?letter='
        all_data = []
        letters = [chr(i) for i in range(ord('A'), ord('Z') + 1)] + ['1']

        for letter in letters:
            log_message(f"Traitement de la lettre: {letter}")

            try: 
                session = requests.Session()
                response = session.get(base_url + letter, headers=headers, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                table = soup.find('table', {'class': 'table nod table--values table--no-auto'})
                if not table:
                    log_message(f"Tableau des actions pour la lettre {letter} non trouvé.")
                    continue
                
                # Parsing des lignes du tableau
                for row in table.find_all('tr')[1:]:  # Ignorer l'en-tête
                    cols = row.find_all('td')
                    if len(cols) >= 7:  # Vérifier qu'on a assez de colonnes
                        try:
                            # Extraction du nom de l'action (colonne 0)
                            nom_element = cols[0].find('a')
                            nom = nom_element.get_text(strip=True) if nom_element else cols[0].get_text(strip=True)
                            
                            # Extraction des valeurs (structure exacte de votre HTML)
                            dernier = cols[1].get_text(strip=True).replace('€', '')  # Cours
                            variation = cols[2].get_text(strip=True)  # Variation
                            ouv = cols[3].get_text(strip=True).replace('€', '')  # Ouverture
                            plus_haut_an = cols[4].get_text(strip=True).replace('€', '')  # + haut
                            plus_bas_an = cols[5].get_text(strip=True).replace('€', '')  # + bas
                            
                            # Nettoyage et conversion des valeurs numériques
                            dernier_clean = dernier.replace('\xa0', '').replace(' ', '').replace(',', '.')
                            dernier_value = float(dernier_clean) if dernier_clean and dernier_clean != '-' else 0.0

                            plus_bas_clean = plus_bas_an.replace('\xa0', '').replace(' ', '').replace(',', '.')
                            plus_bas_value = float(plus_bas_clean) if plus_bas_clean and plus_bas_clean != '-' else 0.0

                            plus_haut_clean = plus_haut_an.replace('\xa0', '').replace(' ', '').replace(',', '.')
                            plus_haut_value = float(plus_haut_clean) if plus_haut_clean and plus_haut_clean != '-' else 0.0

                            # Extraction de la variation en valeur numérique
                            variation_clean = variation.replace('\xa0', '').replace('%', '').replace('+', '').replace(',', '.').replace(' ', '')
                            try:
                                variation_value = float(variation_clean) if variation_clean and variation_clean != '-' else 0.0
                            except ValueError:
                                variation_value = 0.0
                            
                            action_data = {
                                'nom': nom,
                                'dernier': dernier,
                                'dernier_value': dernier_value,
                                'variation': variation,
                                'variation_value': variation_value,
                                'ouverture': ouv,
                                'plus_bas_an': plus_bas_an,
                                'plus_bas_value': plus_bas_value,
                                'plus_haut_an': plus_haut_an,
                                'plus_haut_value': plus_haut_value,
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            all_data.append(action_data)
                            
                        except (ValueError, AttributeError) as e:
                            log_message(f"Erreur parsing ligne pour la lettre {letter}: {e}")
                            continue

            except session.exceptions.RequestException as e:
                log_message(f"Erreur lors de la requête pour la lettre {letter}: {e}")
                continue

            time.sleep(10)  # Pause pour éviter de surcharger le serveur
        
        log_message(f"Total des actions récupérées avec succès : {len(all_data)}")
        return all_data
        
    except Exception as e:
        log_message(f"Erreur lors de la récupération des données: {e}")
        return []

def save_morning_extremes(data):
    """Sauvegarde des extrêmes à l'ouverture (9h00)"""
    try:
        date_str = datetime.now().strftime('%Y%m%d')
        extremes_file = os.path.join(DATA_DIR, f'morning_extremes_{date_str}.json')
        
        morning_data = {}
        for action in data:
            morning_data[action['nom']] = {
                'plus_bas_matin': action['plus_bas_value'],
                'plus_haut_matin': action['plus_haut_value'],
                'cours_ouverture': action['ouverture'],
                'timestamp': action['timestamp']
            }
        
        with open(extremes_file, 'w', encoding='utf-8') as f:
            json.dump(morning_data, f, indent=2)
        
        log_message(f"Extrêmes du matin sauvegardés: {extremes_file}")
        return True
        
    except Exception as e:
        log_message(f"Erreur sauvegarde extrêmes matin: {e}")
        return False

def load_morning_extremes():
    """Chargement des extrêmes du matin"""
    try:
        date_str = datetime.now().strftime('%Y%m%d')
        extremes_file = os.path.join(DATA_DIR, f'morning_extremes_{date_str}.json')
        
        if not os.path.exists(extremes_file):
            log_message(f"Fichier des extrêmes du matin non trouvé: {extremes_file}")
            return None
        
        with open(extremes_file, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        log_message(f"Erreur chargement extrêmes matin: {e}")
        return None

def identify_extremes_actions(evening_data, morning_extremes):
    """Identification des actions ayant atteint les extrêmes annuels"""
    extremes_actions = []
    
    if not morning_extremes:
        log_message("Aucune donnée du matin disponible pour comparaison")
        return extremes_actions
    
    for action in evening_data:
        nom = action['nom']
        if nom in morning_extremes:
            matin_data = morning_extremes[nom]
            
            # Vérifier si le cours du soir est égal au plus haut du matin
            if action['dernier_value'] == matin_data['plus_haut_matin']:
                action['type_extreme'] = 'PLUS HAUT'
                action['niveau_reference'] = matin_data['plus_haut_matin']
                action['variation_jour'] = action['variation']
                extremes_actions.append(action.copy())
            
            # Vérifier si le cours du soir est égal au plus bas du matin
            elif action['dernier_value'] == matin_data['plus_bas_matin']:
                action['type_extreme'] = 'PLUS BAS'
                action['niveau_reference'] = matin_data['plus_bas_matin']
                action['variation_jour'] = action['variation']
                extremes_actions.append(action.copy())
    
    return extremes_actions

def save_to_csv(data, filename):
    """Sauvegarde des données en CSV"""
    try:
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['nom', 'dernier', 'variation_jour', 'type_extreme', 
                         'niveau_reference', 'plus_bas_an', 'plus_haut_an', 'timestamp']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for action in data:
                writer.writerow({
                    'nom': action['nom'],
                    'dernier': action['dernier'],
                    'variation_jour': action.get('variation_jour', action['variation']),
                    'type_extreme': action.get('type_extreme', ''),
                    'niveau_reference': action.get('niveau_reference', ''),
                    'plus_bas_an': action['plus_bas_an'],
                    'plus_haut_an': action['plus_haut_an'],
                    'timestamp': action['timestamp']
                })
        
        log_message(f"Fichier CSV sauvegardé: {filename}")
        return filepath
        
    except Exception as e:
        log_message(f"Erreur sauvegarde CSV: {e}")
        return None
  

def send_email_with_attachment(csv_filepath, extremes_count):
    """Envoi de l'email avec pièce jointe via Gmail."""
    try:
        # Préparation du message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_CONFIG['sender_email']
        msg['To'] = ", ".join(RECIPIENTS)
        
        # Sujet de l'email
        date_str = datetime.now().strftime('%d/%m/%Y')
        if extremes_count > 0:
            msg['Subject'] = f"🚨 Alerte SRD - {extremes_count} actions aux extrêmes le {date_str}"
        else:
            msg['Subject'] = f"Rapport SRD - Aucune action aux extrêmes le {date_str}"
        
        # Corps de l'email
        body = f"""
        <html>
        <body>
            <h2>Rapport des actions SRD du {date_str}</h2>
            <p>Bonjour,</p>
            <p>Voici le rapport des actions du SRD ayant atteint leur plus haut ou plus bas de l'année aujourd'hui.</p>
            <p>Nombre d'actions aux extrêmes identifiées: <strong>{extremes_count}</strong></p>
            <p>Le fichier CSV contenant toutes les données est joint à cet email.</p>
            <br>
            <p><strong>Méthodologie:</strong> Comparaison entre les extrêmes à l'ouverture (9h00) et les cours de clôture (18h30).</p>
            <p>Cordialement,<br>Votre robot SRD</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attachement du fichier CSV
        with open(csv_filepath, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="csv")
            attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(csv_filepath))
            msg.attach(attach)
        
        # Connexion et envoi via Gmail SMTP
        with smtplib.SMTP(GMAIL_CONFIG['smtp_server'], GMAIL_CONFIG['smtp_port']) as server:
            server.starttls()  # Sécurisation de la connexion
            server.login(GMAIL_CONFIG['sender_email'], GMAIL_CONFIG['app_password'])
            server.sendmail(GMAIL_CONFIG['sender_email'], RECIPIENTS, msg.as_string())
        
        print("✅ Email envoyé avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur envoi email avec Gmail: {e}")
        return False

def should_run_morning():
    """Détermine si on doit exécuter la capture du matin"""
    now = datetime.now()
    return now.weekday() < 5 and now.time().hour == 9 and now.time().minute <= 5

def should_run_evening():
    """Détermine si on doit exécuter l'analyse du soir"""
    now = datetime.now()
    return now.weekday() < 5 and now.time().hour == 18 and now.time().minute >= 30


def cleanup_yesterday_files(directory):
    """Conserve uniquement les fichiers de la veille et supprime les autres."""
    current_date = datetime.now()
    yesterday_date = current_date - timedelta(days=1)
    yesterday_str = yesterday_date.strftime('%Y%m%d')

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            # Si le nom du fichier contient la date d'hier, on le conserve
            if yesterday_str in filename:
                log_message(f"Fichier conservé (hier): {file_path}")
                continue
            try:
                # Supprime le fichier s'il ne correspond pas à la date d'hier
                os.remove(file_path)
                log_message(f"Fichier supprimé: {file_path}")
            except Exception as e:
                log_message(f"Impossible de supprimer {file_path}: {e}")


def main():
    """Fonction principale"""
    log_message("=== DÉMARRAGE DU SCRAPING SRD ===")
    
    now = datetime.now()
    
    # Vérification du week-end
    # if now.weekday() >= 5:  # Weekend (5=samedi, 6=dimanche)
    #     log_message("Arrêt: Week-end - pas d'analyse nécessaire")
    #     return
    
    # Exécution à 9h00 (capture des extrêmes du matin)
    if should_run_morning():
    # if True:
        log_message("=== CAPTURE DES EXTRÊMES DU MATIN ===")
        srd_data = fetch_srd_data()
        if srd_data:
            save_morning_extremes(srd_data)
        else:
            log_message("Échec de la capture des données du matin")
        return
    
    # Exécution à 18h30 (analyse comparative)
    # if should_run_evening():
    if True :
        log_message("=== ANALYSE COMPARATIVE SOIR ===")
        
        # Chargement des extrêmes du matin
        morning_extremes = load_morning_extremes()
        if not morning_extremes:
            log_message("Erreur: Données du matin non disponibles")
            return
        
        # Récupération des données du soir
        evening_data = fetch_srd_data()
        if not evening_data:
            log_message("Arrêt: Aucune donnée récupérée le soir")
            return
        
        # Identification des actions aux extrêmes
        extremes_actions = identify_extremes_actions(evening_data, morning_extremes)
        
        # Sauvegarde des résultats
        date_str = datetime.now().strftime('%Y%m%d')
        extremes_file = save_to_csv(extremes_actions, f"srd_extremes_{date_str}.csv")
        
        # Envoi de l'email avec les résultats
        if extremes_file:
            send_email_with_attachment(extremes_file, len(extremes_actions))
        else:
            log_message("Aucun fichier CSV généré pour l'envoi")
        
        log_message(f"{len(extremes_actions)} actions aux extrêmes identifiées")
        # Appel de la fonction de nettoyage
        cleanup_yesterday_files(DATA_DIR)
    
    else:
        log_message("Arrêt: Exécution uniquement à 9h00 et 18h30")
    
    log_message("=== SCRAPING TERMINÉ ===")

if __name__ == "__main__":
    main()