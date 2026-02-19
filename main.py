import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
from googlesearch import search

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458134397986406482/ncQJKY8zdbG3IYrczVMug8i-1P_OVMhSqIYq8giw7UVttj-Ch-2aaKFZIIGl7cNLfruF"
CHECK_INTERVAL = 43200  # 12h en secondes

class JobOffer:
    def __init__(self, title, link, location="N/C", source="Inconnue", status="active"):
        self.title = title
        self.link = link
        self.location = location
        self.source = source
        self.status = status

# --- SCANNERS ---
def scan_clair_group():
    print("--- Scan de Clair Group ---")
    url = "https://www.clair-group.com/fr/recrutement/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    found = []
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            page_text = soup.get_text().lower()
            
            # D'abord chercher les offres actives
            for item in soup.find_all(['h3', 'a', 'div'], class_=['job', 'offer', 'title']):
                text = item.get_text(strip=True).lower()
                if any(k in text for k in ["pilote", "pnt", "commandant", "officier", "captain", "f/o"]):
                    link = item['href'] if item.name == 'a' and item.has_attr('href') else url
                    if not link.startswith('http'): 
                        link = "https://www.clair-group.com" + link
                    found.append(JobOffer(text.capitalize(), link, "Guyancourt / Le Bourget", "Clair Group"))
            
            # Si aucune offre trouvée, chercher les balises/liens avec mots-clés
            if not found:
                for a in soup.find_all('a', href=True):
                    text = a.get_text(strip=True).lower()
                    if any(k in text for k in ["pilote", "pnt", "captain", "candidature"]):
                        link = a['href']
                        if not link.startswith('http'):
                            link = "https://www.clair-group.com" + link
                        found.append(JobOffer(text.capitalize(), link, "Guyancourt / Le Bourget", "Clair Group"))
            
            # Si toujours aucune offre ET message "complet" présent
            if not found and any(k in page_text for k in ["effectifs complets", "pas de recrutement", "no vacancy"]):
                return [JobOffer("Pas d'offre d'emploi à ce jour", url, "Le Bourget", "Clair Group", status="full")]
        
    except Exception as e:
        print(f"Erreur Clair Group: {e}")
    
    return found

def scan_jetfly():
    print("--- Scan de Jetfly (Filtre OPS actif) ---")
    api_url = "https://jetfly.bamboohr.com/careers/list"
    found = []
    try:
        r = requests.get(api_url, timeout=10)
        if r.status_code == 200:
            jobs = r.json().get('result', [])
            for j in jobs:
                title = j.get('jobOpeningName', '')
                title_low = title.lower()
                # 1. On vérifie que c'est bien un job de pilote
                if any(k in title_low for k in ["pilot", "captain", "first officer", "f/o"]):
                    # 2. On EXCLUT les postes au sol / bureau
                    ops_keywords = ["ground", "dispatch", "ops", "sales", "office", "accountant", "mechanic", "technician"]
                    if not any(ok in title_low for ok in ops_keywords):
                        found.append(JobOffer(title, f"https://jetfly.bamboohr.com/careers/{j.get('id')}", j.get('location', 'N/C'), "Jetfly"))
    except Exception as e:
        print(f"Erreur Jetfly: {e}")
    
    return found

def scan_oyonnair():
    print("--- Scan de Oyonnair ---")
    url = "https://www.oyonnair.com/compagnie-aerienne/recrutement/"
    found = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            page_text = soup.get_text().lower()
            
            # IMPORTANT: Vérifier DIRECTEMENT si les effectifs sont complets
            if "effectifs sont complets" in page_text or "effectifs complets" in page_text:
                return [JobOffer("Effectifs complets", url, "Lyon/Rennes", "Oyonnair", status="full")]
            
            # Sinon, chercher des offres actives réelles
            # On cherche uniquement dans les titres h2/h3 ou les liens spécifiques
            for elem in soup.find_all(['h2', 'h3', 'a']):
                text = elem.get_text(strip=True).lower()
                
                # Exclure les phrases génériques de présentation
                exclusions = ["régulièrement à la recherche", "rejoignez-nous", "recrutement", 
                             "différents domaines", "tels que", "compagnie-aerienne"]
                
                # Chercher les offres pilotes réelles (titre court et précis)
                if any(k in text for k in ["pilote", "pnt", "commandant", "capitaine", "captain"]):
                    if not any(ex in text for ex in exclusions) and len(text) < 100:
                        if elem.name == 'a' and elem.has_attr('href') and 'recrutement' not in elem['href']:
                            link = elem['href']
                            if not link.startswith('http'):
                                link = "https://www.oyonnair.com" + link
                            found.append(JobOffer(text.capitalize(), link, "Lyon/Rennes", "Oyonnair"))
            
            # Supprimer les doublons
            seen = set()
            unique_found = []
            for job in found:
                if job.title not in seen:
                    seen.add(job.title)
                    unique_found.append(job)
            
            return unique_found
                
    except Exception as e:
        print(f"Erreur Oyonnair: {e}")
    
    return found

def scan_netjets():
    print("--- Scan de NetJets Europe ---")
    url = "https://netjets.jobs.hr.cloud.sap/europe/search/?createNewAlert=false&q=pilot&locationsearch=&optionsFacetsDD_location=&optionsFacetsDD_department="
    base_url = "https://netjets.jobs.hr.cloud.sap"
    found = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Les offres sont dans un tableau, chaque ligne contient titre + location
            rows = soup.find_all('tr')
            for row in rows:
                link_tag = row.find('a', href=True)
                if not link_tag:
                    continue
                
                title = link_tag.get_text(strip=True)
                href = link_tag['href']
                if not href.startswith('http'):
                    href = base_url + href
                
                # Récupérer les cellules <td> pour extraire la localisation
                cells = row.find_all('td')
                location = "N/C"
                if len(cells) >= 2:
                    location = cells[1].get_text(strip=True)
                
                # Filtrer uniquement les postes pilotes
                title_low = title.lower()
                if any(k in title_low for k in ["pilot", "captain", "first officer", "second in command", "f/o", "pic", "sic"]):
                    found.append(JobOffer(title, href, location, "NetJets Europe"))
            
            if not found:
                # Vérifier si aucune offre disponible
                page_text = soup.get_text().lower()
                if "no results" in page_text or "0 result" in page_text:
                    return [JobOffer("Aucune offre disponible actuellement", url, "Europe", "NetJets Europe", status="full")]
                    
    except Exception as e:
        print(f"Erreur NetJets: {e}")
    
    return found

def scan_pan_european():
    print("--- Scan de Pan Européenne ---")
    url = "https://www.paneuropeenne.com/en/"
    found = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Chercher les offres actives
            for elem in soup.find_all(['h2', 'h3', 'h4', 'div', 'p', 'li', 'a']):
                text = elem.get_text(strip=True).lower()
                # Chercher les offres pilotes
                if any(k in text for k in ["pilot", "captain", "first officer", "f/o", "pnt"]):
                    # Éviter les phrases génériques
                    if len(text) > 10 and len(text) < 200 and "no employment" not in text:
                        link = url
                        if elem.name == 'a' and elem.has_attr('href'):
                            link = elem['href']
                            if not link.startswith('http'):
                                link = "https://www.paneuropeenne.com" + link
                        found.append(JobOffer(text.capitalize(), link, "Chambéry", "Pan Européenne"))
            
            # Supprimer les doublons
            seen = set()
            unique_found = []
            for job in found:
                if job.title not in seen:
                    seen.add(job.title)
                    unique_found.append(job)
            found = unique_found
            
            # Si aucune offre ET message "no employment" présent
            if not found and "no employment at the moment" in page_text:
                return [JobOffer("Effectifs complets", url, "Chambéry", "Pan Européenne", status="full")]
                
    except Exception as e:
        print(f"Erreur Pan Européenne: {e}")
    
    return found

def scan_chalair():
    print("--- Scan de Chalair ---")
    url = "https://www.chalair.fr/offres-emplois"
    found, seen = [], set()
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Chercher les offres d'emploi spécifiques
            for a in soup.find_all('a', href=True):
                text = a.get_text(strip=True).lower()
                href_lower = a['href'].lower()
                
                if any(k in text or k in href_lower for k in ["candidature", "pnt", "pilote", "captain", "recrutement"]):
                    u = a['href'] if a['href'].startswith('http') else f"https://www.chalair.fr{a['href']}"
                    if u not in seen and len(text) > 5:
                        found.append(JobOffer(text.capitalize() if text else "Candidature PNT", u, "France", "Chalair"))
                        seen.add(u)
                        
    except Exception as e:
        print(f"Erreur Chalair: {e}")
    
    return found

def scan_pcc():
    print("--- Scan de Pilot Career Center ---")
    url = "https://pilotcareercenter.com/PILOT-JOB-NAVIGATOR/EUROPE-UK/"
    found = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            t = a.get_text(strip=True)
            if any(k in t.lower() for k in ["first officer", "f/o", "pilot", "low hour"]):
                trash = ["add pilot", "training", "resume", "cv", "interview", "help", "post", "advertise", "payscale", "roadshows"]
                if not any(tr in t.lower() for tr in trash) and len(t) > 10:
                    link = a['href'] if a['href'].startswith('http') else f"https://pilotcareercenter.com{a['href']}"
                    found.append(JobOffer(t, link, "Europe", "PCC"))
                    
    except Exception as e:
        print(f"Erreur PCC: {e}")
    
    return found

# --- DISCORD ---
def send_to_discord(jetfly, pcc, chalair, oyo, pan, clair, netjets):
    now = datetime.now()
    next_scan = now + timedelta(seconds=CHECK_INTERVAL)
    embeds = []
    
    def add_section(title, jobs, color=15158332, custom_msg=None):
        if custom_msg:
            embeds.append({"title": title, "color": 0x95a5a6, "description": f"⏳ *{custom_msg}*"})
            return
        if not jobs:
            embeds.append({"title": title, "color": 0x2f3136, "description": "⚪ *Aucun poste répertorié à ce jour.*"})
            return
        if jobs[0].status == "full":
            embeds.append({"title": title, "color": 0x2f3136, "description": "🔴 **Effectifs complets à ce jour.**\n*Il est toutefois envisageable de soumettre une candidature spontanée.*"})
        else:
            fields = [{"name": f"✅ {j.title}", "value": f"[Accéder à l'offre]({j.link})", "inline": False} for j in jobs]
            embeds.append({"title": title, "color": color, "fields": fields[:25]})
    
    add_section("🏢 OYONNAIR", oyo)
    add_section("🏢 PAN EUROPÉENNE", pan)
    add_section("🏢 CLAIR GROUP (AstonJet/Fly)", clair)
    add_section("🏢 AIRLEC", None, custom_msg="Processus d'implémentation en cours...")
    add_section("🏢 CHALAIR", chalair)
    add_section("🏢 JETFLY", jetfly, color=3447003)
    add_section("🌍 PILOT CAREER CENTER", pcc, color=15105570)
    add_section("✈️ NETJETS EUROPE", netjets, color=1752220)
    
    payload = {
        "username": "Aero Job Monitor",
        "content": f"📝 **RAPPORT DE VEILLE AÉRONAUTIQUE DU {now.strftime('%d/%m/%Y à %H:%M')}**\n📅 *Prochaine actualisation prévue le : {next_scan.strftime('%d/%m/%Y à %H:%M')}*",
        "embeds": embeds[:10]
    }
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
        print("✅ Rapport envoyé sur Discord")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi Discord: {e}")

if __name__ == "__main__":
    while True:
        print(f"\n=== PROTOCOLE DE SCAN INITIALISÉ LE {datetime.now().strftime('%d/%m/%Y %H:%M')} ===")
        
        j = scan_jetfly()
        p = scan_pcc()
        c = scan_chalair()
        o = scan_oyonnair()
        pan = scan_pan_european()
        cl = scan_clair_group()
        nj = scan_netjets()
        
        send_to_discord(j, p, c, o, pan, cl, nj)
        print(f"Procédure terminée. Attente de {CHECK_INTERVAL/3600}h.")
        time.sleep(CHECK_INTERVAL)