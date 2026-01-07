import requests
from bs4 import BeautifulSoup
import time
from googlesearch import search

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458134397986406482/ncQJKY8zdbG3IYrczVMug8i-1P_OVMhSqIYq8giw7UVttj-Ch-2aaKFZIIGl7cNLfruF"
CHECK_INTERVAL = 86400  

class JobOffer:
    def __init__(self, title, link, location="N/C", source="Inconnue", status="active"):
        self.title = title
        self.link = link
        self.location = location
        self.source = source
        self.status = status

# --- SCANNERS ---

def scan_oyonnair():
    print("--- Scan d'Oyonnair ---")
    url = "https://www.oyonnair.com/compagnie-aerienne/recrutement/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    found = []
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            page_text = soup.get_text().lower()
            if "effectifs sont complets à ce jour" in page_text or "effectifs complets" in page_text:
                return [JobOffer("Effectifs complets", url, "Lyon/Rennes", "Oyonnair", status="full")]

            for item in soup.find_all(['h2', 'h3', 'a', 'span']):
                text = item.get_text(strip=True).lower()
                if any(k in text for k in ["pilote", "pnt", "officier", "captain", "copilote"]):
                    parent_a = item.find_parent('a') or (item if item.name == 'a' else None)
                    link = parent_a['href'] if parent_a else url
                    if not link.startswith('http'): link = "https://www.oyonnair.com" + link
                    if not any(f.link == link for f in found):
                        found.append(JobOffer(f"Oyonnair - {text.capitalize()}", link, "Lyon / Rennes", "Oyonnair"))
    except: pass
    return found

def scan_pan_european():
    print("--- Scan de Pan Européenne ---")
    url = "https://www.paneuropeenne.com/en/" 
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            content = soup.get_text().lower()
            if "no employment at the moment" in content or "no response by phone" in content:
                return [JobOffer("Effectifs complets", url, "Chambéry/Lyon", "Pan Europe", status="full")]
            
            if any(k in content for k in ["pilot", "officer", "captain", "hiring"]):
                return [JobOffer("Ouverture de poste !", url, "Chambéry", "Pan Europe")]
    except: pass
    return []

def scan_chalair():
    print("--- Scan de Chalair ---")
    url = "https://www.chalair.fr/offres-emplois"
    headers = {'User-Agent': 'Mozilla/5.0'}
    found = []
    seen_links = set() 
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(strip=True).lower()
                
                # On cherche les mots clés
                if any(k in text or k in href.lower() for k in ["candidature", "pnt", "pilote", "skeeled"]):
                    full_url = href if href.startswith('http') else f"https://www.chalair.fr{href}"
                    
                    # Nettoyage : Si c'est un lien vers leur plateforme de recrutement "Skeeled"
                    # ou un lien contenant PNT, on ne l'ajoute qu'une seule fois.
                    if full_url not in seen_links:
                        found.append(JobOffer("Candidature PNT / Spontanée", full_url, "France", "Chalair"))
                        seen_links.add(full_url)
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
                if any(k in title.lower() for k in ["pilot", "captain", "first officer"]):
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
            if any(k in title.lower() for k in ["pilote", "largueur", "be90", "be200", "c208"]):
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
                # Filtres d'exclusion (payscale, roadshow, etc.)
                trash = ["add pilot","training", "resume", "cv", "interview", "help", "post", "advertise", "payscale", "roadshows"]
                if not any(t in title.lower() for t in trash) and len(title) > 10:
                    link = a['href'] if a['href'].startswith('http') else f"https://pilotcareercenter.com{a['href']}"
                    found.append(JobOffer(title, link, "Europe / UK", "PCC"))
    except: pass
    return found

def scan_google_radar():
    print("--- Scan Radar Google ---")
    query = '(intitle:"recrutement" OR "offre d\'emploi" OR "Ab-initio") AND ("pilote" OR "pilot") AND ("C206" OR "PC6" OR "B200" OR "largueur")'
    found = []
    try:
        for url in search(query, num_results=10, lang="fr"):
            if not any(x in url for x in ["youtube", "facebook", "instagram"]):
                found.append(JobOffer("Radar Web (Ab-initio/Job)", url, "Web", "Google"))
    except: pass
    return found

# --- DISCORD ---

def send_to_discord(jetfly, aero, pcc, radar, chalair, oyo, pan):
    embeds = []

    # Section Pan Européenne
    if pan:
        if pan[0].status == "full":
            embeds.append({"title": "🏢 PAN EUROPÉENNE", "color": 0x2f3136, "description": "🔴 **No employment at the moment.**\n*Monitoring en cours...*"})
        else:
            fields = [{"name": "🔥 CHANGEMENT DÉTECTÉ", "value": f"[Vérifier Pan Européenne]({pan[0].link})", "inline": False}]
            embeds.append({"title": "🏢 PAN EUROPÉENNE", "color": 15158332, "fields": fields})
    else:
        embeds.append({"title": "🏢 PAN EUROPÉENNE", "color": 0x2f3136, "description": "⚪ *Inaccessible.*"})

    # Section Oyonnair
    if oyo:
        if any(o.status == "full" for o in oyo):
            embeds.append({"title": "🏢 OYONNAIR", "color": 0x2f3136, "description": "🔴 **Effectifs complets à ce jour.**\n*Monitoring en cours...*"})
        else:
            fields = [{"name": f"✅ {o.title}", "value": f"[Lien direct]({o.link})", "inline": False} for o in oyo]
            embeds.append({"title": "🏢 OYONNAIR", "color": 15158332, "fields": fields})
    else:
        embeds.append({"title": "🏢 OYONNAIR", "color": 0x2f3136, "description": "⚪ *Aucune donnée.*"})

    # Helper pour les autres
    def add_section(title, color, jobs, empty_msg="Aucune offre."):
        if jobs:
            fields = [{"name": f"✅ {j.title}", "value": f"[Lien direct]({j.link})", "inline": False} for j in jobs]
            embeds.append({"title": title, "color": color, "fields": fields[:25]})
        else:
            embeds.append({"title": title, "color": 0x2f3136, "description": f"⚪ *{empty_msg}*"})

    add_section("🏢 CHALAIR", 15158332, chalair)
    add_section("🏢 JETFLY", 3447003, jetfly)
    add_section("🌍 PILOT CAREER CENTER", 15105570, pcc)

    combined_web = aero + radar
    seen_links = set()
    final_web = []
    for j in combined_web:
        if j.link not in seen_links:
            final_web.append(j)
            seen_links.add(j.link)
    add_section("🔎 RADAR WEB & AB-INITIO", 15844367, final_web)

    payload = {"username": "Aero Job Monitor", "content": "📅 **RAPPORT DE SCAN QUOTIDIEN**", "embeds": embeds[:10]}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print("Rapport envoyé !")

if __name__ == "__main__":
    while True:
        print("\n=== DÉMARRAGE DU SCAN GLOBAL ===")
        j = scan_jetfly()
        a = scan_aerocontact()
        p = scan_pcc()
        r = scan_google_radar()
        c = scan_chalair()
        o = scan_oyonnair()
        pan = scan_pan_european()
        
        send_to_discord(j, a, p, r, c, o, pan)
        
        print(f"Terminé. Sommeil 24h.")
        time.sleep(CHECK_INTERVAL)