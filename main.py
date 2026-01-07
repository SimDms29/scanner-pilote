import requests
from bs4 import BeautifulSoup
import time
from googlesearch import search

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458134397986406482/ncQJKY8zdbG3IYrczVMug8i-1P_OVMhSqIYq8giw7UVttj-Ch-2aaKFZIIGl7cNLfruF"
CHECK_INTERVAL = 86400  

class JobOffer:
    def __init__(self, title, link, location="N/C", source="Inconnue"):
        self.title = title
        self.link = link
        self.location = location
        self.source = source

# --- SCANNERS ---

def scan_jetfly():
    print("--- Scan de Jetfly ---")
    api_url = "https://jetfly.bamboohr.com/careers/list"
    found = []
    try:
        r = requests.get(api_url, timeout=10)
        if r.status_code == 200:
            jobs = r.json().get('result', [])
            for j in jobs:
                title = j.get('jobOpeningName', '')
                if any(k in title.lower() for k in ["pilot", "captain", "first officer", "f/o", "pc-12"]):
                    found.append(JobOffer(title, f"https://jetfly.bamboohr.com/careers/{j.get('id')}", j.get('location', 'N/C'), "Jetfly"))
    except: pass
    return found

def scan_aerocontact():
    print("--- Scan Aerocontact ---")
    url = "https://www.aerocontact.com/offres-emploi-aeronautique/metier-pilote-21"
    found = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for h2 in soup.find_all('h2'):
            title = h2.get_text(strip=True)
            if any(k in title.lower() for k in ["pilote", "largueur", "be90", "be200", "c208", "para"]):
                link_tag = h2.find('a')
                if link_tag:
                    link = link_tag['href']
                    if not link.startswith('http'): link = "https://www.aerocontact.com" + link
                    found.append(JobOffer(title, link, "France", "Aerocontact"))
    except: pass
    return found

def scan_pcc():
    print("--- Scan Pilot Career Center ---")
    url = "https://pilotcareercenter.com/PILOT-JOB-NAVIGATOR/EUROPE-UK/"
    found = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            title = a.get_text(strip=True)
            if any(k in title.lower() for k in ["first officer", "f/o", "pilot", "low hour", "non type rated"]):
                trash = ["add pilot","training", "resume", "cv", "interview", "help", "post", "advertise"]
                if not any(t in title.lower() for t in trash) and len(title) > 10:
                    link = a['href'] if a['href'].startswith('http') else f"https://pilotcareercenter.com{a['href']}"
                    found.append(JobOffer(title, link, "Europe / UK", "PCC"))
    except: pass
    return found

def scan_chalair():
    print("--- Scan de Chalair ---")
    url = "https://chalair.skeeled.com/" 
    found = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for job_card in soup.find_all(['h3', 'h4', 'span']):
            title = job_card.get_text(strip=True)
            if any(k in title.lower() for k in ["pilote", "officier", "captain", "f/o"]):
                parent_a = job_card.find_parent('a') or job_card.find('a')
                link = parent_a['href'] if parent_a else url
                if not link.startswith('http'): link = "https://chalair.skeeled.com" + link
                found.append(JobOffer(title, link, "France", "Chalair"))
    except: pass
    return found

def scan_google_radar():
    print("--- Scan Radar Google ---")
    query = '(intitle:"recrutement" OR "offre d\'emploi") AND ("pilote" OR "pilot") AND ("C206" OR "PC6" OR "B200" OR "largueur" OR "parachutisme")'
    found = []
    try:
        for url in search(query, num_results=10, lang="fr"):
            if not any(x in url for x in ["youtube", "facebook", "instagram"]):
                found.append(JobOffer("Radar Web", url, "Web", "Google"))
    except: pass
    return found

# --- DISCORD ---

def send_to_discord(jetfly, aero, pcc, radar, chalair):
    embeds = []

    # 1. JETFLY
    if jetfly:
        fields = [{"name": f"✈️ {j.title}", "value": f"📍 {j.location}\n[Postuler]({j.link})", "inline": False} for j in jetfly]
        embeds.append({"title": "🏢 JETFLY", "color": 3447003, "fields": fields[:25]})

    # 2. CHALAIR
    if chalair:
        fields = [{"name": f"🇫🇷 {j.title}", "value": f"[Postuler chez Chalair]({j.link})", "inline": False} for j in chalair]
        embeds.append({"title": "🏢 CHALAIR", "color": 15158332, "fields": fields})

    # 3. PCC
    if pcc:
        fields = [{"name": f"🌍 {j.title}", "value": f"[Lien PCC]({j.link})", "inline": False} for j in pcc]
        embeds.append({"title": "🎯 PILOT CAREER CENTER", "color": 15105570, "fields": fields[:25]})

    # 4. AEROCONTACT & RADAR
    combined_web = aero + radar
    if combined_web:
        fields = [{"name": f"🔎 {j.title}", "value": f"[Voir l'offre]({j.link})", "inline": False} for j in combined_web]
        embeds.append({"title": "📢 RADAR WEB & ANNONCES", "color": 15844367, "fields": fields[:25]})

    # 5. CANDIDATURES SPONTANÉES (Toujours affiché)
    spontanees = [
        {"name": "🚁 Valljet (Affaires)", "value": "📧 recrutement@valljet.com", "inline": True},
        {"name": "🚑 Oyonnair (Evasan)", "value": "📧 rh@oyonnair.com", "inline": True},
        {"name": "🏥 Airlec (Ambulance)", "value": "📧 info@airlec.eu", "inline": True},
        {"name": "📦 Pan Européenne", "value": "📧 info@paneuropeenne.com", "inline": True},
        {"name": "🦅 Finist'air", "value": "📧 contact@finistair.fr", "inline": True}
    ]
    embeds.append({
        "title": "📩 CANDIDATURES SPONTANÉES (Cibles prioritaires)",
        "description": "Ces compagnies ne postent pas toujours d'offres, contacte-les directement !",
        "color": 3066993, # Vert
        "fields": spontanees
    })

    payload = {
        "username": "Aero Job Monitor",
        "content": "📅 **Résumé des opportunités du jour**",
        "embeds": embeds[:10]
    }
    
    requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print("Résumé envoyé sur Discord !")

# --- MAIN ---

if __name__ == "__main__":
    while True:
        print("\n=== DÉMARRAGE DU SCAN GLOBAL ===")
        
        jet_jobs = scan_jetfly()
        aero_jobs = scan_aerocontact()
        pcc_jobs = scan_pcc()
        radar_jobs = scan_google_radar()
        chalair_jobs = scan_chalair()
        
        send_to_discord(jet_jobs, aero_jobs, pcc_jobs, radar_jobs, chalair_jobs)
        
        print(f"Terminé. Prochain passage dans 24h.")
        time.sleep(CHECK_INTERVAL)