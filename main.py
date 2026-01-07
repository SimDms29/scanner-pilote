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

def scan_chalair():
    print("--- Scan de Chalair ---")
    url = "https://www.chalair.fr/offres-emplois"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    found = []
    seen_links = set()
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(strip=True).lower()
                
                # On cible les liens pertinents
                if any(k in text or k in href.lower() for k in ["candidature", "pnt", "pilote", "skeeled"]):
                    full_url = href if href.startswith('http') else f"https://www.chalair.fr{href}"
                    
                    # LOGIQUE : Si on a déjà un lien "PNT" spécifique, on ignore le lien "candidature" général
                    if "pnt" in full_url.lower() or "pnt" in text:
                        # On supprime un éventuel lien général déjà ajouté
                        found = [f for f in found if "pnt" in f.link.lower()]
                        
                    if full_url not in seen_links:
                        # On évite de rajouter le général si on a déjà un spécifique
                        if "pnt" not in full_url.lower() and any("pnt" in l for l in seen_links):
                            continue
                            
                        found.append(JobOffer("Candidature PNT / Spontanée", full_url, "France", "Chalair"))
                        seen_links.add(full_url)
                        print(f"✅ Lien Chalair retenu : {full_url}")
    except: pass
    return found

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
            if any(k in title.lower() for k in ["first officer", "f/o", "pilot", "low hour"]):
                trash = ["add pilot","training", "resume", "cv", "interview", "help", "post", "advertise", "payscale", "roadshow"]
                if not any(t in title.lower() for t in trash) and len(title) > 10:
                    link = a['href'] if a['href'].startswith('http') else f"https://pilotcareercenter.com{a['href']}"
                    found.append(JobOffer(title, link, "Europe / UK", "PCC"))
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
    if not any([jetfly, aero, pcc, radar, chalair]):
        print("Aucune offre trouvée.")
        return

    embeds = []

    if jetfly:
        fields = [{"name": f"✈️ {j.title}", "value": f"📍 {j.location}\n[Postuler]({j.link})", "inline": False} for j in jetfly]
        embeds.append({"title": "🏢 JETFLY", "color": 3447003, "fields": fields[:25]})

    if chalair:
        fields = [{"name": f"🇫🇷 {j.title}", "value": f"[Accéder à l'offre]({j.link})", "inline": False} for j in chalair]
        embeds.append({"title": "🏢 CHALAIR", "color": 15158332, "fields": fields})

    if pcc:
        fields = [{"name": f"🌍 {j.title}", "value": f"[Lien PCC]({j.link})", "inline": False} for j in pcc]
        embeds.append({"title": "🎯 PILOT CAREER CENTER", "color": 15105570, "fields": fields[:25]})

    combined_web = aero + radar
    if combined_web:
        seen_radar = set()
        final_web = []
        for j in combined_web:
            if j.link not in seen_radar:
                final_web.append(j)
                seen_radar.add(j.link)
        
        fields = [{"name": f"🔎 {j.title}", "value": f"[Voir l'offre]({j.link})", "inline": False} for j in final_web]
        embeds.append({"title": "📢 RADAR WEB & ANNONCES", "color": 15844367, "fields": fields[:25]})

    payload = {"username": "Aero Job Monitor", "content": "📅 **Résumé du jour**", "embeds": embeds[:10]}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print("Résumé envoyé sur Discord !")

if __name__ == "__main__":
    while True:
        print("\n=== DÉMARRAGE DU SCAN GLOBAL ===")
        jet = scan_jetfly()
        aero = scan_aerocontact()
        pcc = scan_pcc()
        radar = scan_google_radar()
        chal = scan_chalair()
        
        send_to_discord(jet, aero, pcc, radar, chal)
        print(f"Terminé. Sommeil 24h.")
        time.sleep(CHECK_INTERVAL)