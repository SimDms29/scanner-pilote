import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
from googlesearch import search

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458134397986406482/ncQJKY8zdbG3IYrczVMug8i-1P_OVMhSqIYq8giw7UVttj-Ch-2aaKFZIIGl7cNLfruF"
CHECK_INTERVAL = 7200 # 2h en secondes

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
            # On cherche les blocs d'offres (souvent dans des h3 ou des liens)
            for item in soup.find_all(['h3', 'a', 'div'], class_=['job', 'offer', 'title']):
                text = item.get_text(strip=True).lower()
                if any(k in text for k in ["pilote", "pnt", "commandant", "officier", "captain", "f/o"]):
                    link = item['href'] if item.name == 'a' and item.has_attr('href') else url
                    if not link.startswith('http'): link = "https://www.clair-group.com" + link
                    found.append(JobOffer(text.capitalize(), link, "Guyancourt / Le Bourget", "Clair Group"))
        
        if not found:
            # Si aucun job pilote n'est listé, on considère les effectifs complets
            return [JobOffer("Pas d'offre d'emploi à ce jour", url, "Le Bourget", "Clair Group", status="full")]
    except: pass
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
    except: pass
    return found

# [Les autres scanners : oyonnair, pan_european, chalair, pcc restent identiques]

def scan_oyonnair():
    print("--- Scan de Oyonnair ---")
    url = "https://www.oyonnair.com/compagnie-aerienne/recrutement/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code == 200:
            page_text = BeautifulSoup(r.text, 'html.parser').get_text().lower()
            if "effectifs sont complets" in page_text or "effectifs complets" in page_text:
                return [JobOffer("Effectifs complets", url, "Lyon/Rennes", "Oyonnair", status="full")]
    except: pass
    return []

def scan_pan_european():
    print("--- Scan de Pan Européenne ---")
    url = "https://www.paneuropeenne.com/en/" 
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code == 200:
            if "no employment at the moment" in BeautifulSoup(r.text, 'html.parser').get_text().lower():
                return [JobOffer("Effectifs complets", url, "Chambéry", "Pan Européenne", status="full")]
    except: pass
    return []

def scan_chalair():
    print("--- Scan de Chalair ---")
    url = "https://www.chalair.fr/offres-emplois"
    found, seen = [], set()
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code == 200:
            for a in BeautifulSoup(r.text, 'html.parser').find_all('a', href=True):
                if any(k in a.get_text().lower() or k in a['href'].lower() for k in ["candidature", "pnt", "pilote"]):
                    u = a['href'] if a['href'].startswith('http') else f"https://www.chalair.fr{a['href']}"
                    if u not in seen:
                        found.append(JobOffer("Candidature PNT", u, "France", "Chalair"))
                        seen.add(u)
    except: pass
    return found

def scan_pcc():
    print("--- Scan de Pilot Career Center ---")
    url = "https://pilotcareercenter.com/PILOT-JOB-NAVIGATOR/EUROPE-UK/"
    found = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        for a in BeautifulSoup(r.text, 'html.parser').find_all('a', href=True):
            t = a.get_text(strip=True)
            if any(k in t.lower() for k in ["first officer", "f/o", "pilot", "low hour"]):
                trash = ["add pilot","training", "resume", "cv", "interview", "help", "post", "advertise", "payscale", "roadshows"]
                if not any(tr in t.lower() for tr in trash) and len(t) > 10:
                    found.append(JobOffer(t, a['href'] if a['href'].startswith('http') else f"https://pilotcareercenter.com{a['href']}", "Europe", "PCC"))
    except: pass
    return found

# --- DISCORD ---

def send_to_discord(jetfly, pcc, chalair, oyo, pan, clair):
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

    payload = {
        "username": "Aero Job Monitor",
        "content": f"📝 **RAPPORT DE VEILLE AÉRONAUTIQUE DU {now.strftime('%d/%m/%Y à %H:%M')}**\n📅 *Prochaine actualisation prévue le : {next_scan.strftime('%d/%m/%Y à %H:%M')}*",
        "embeds": embeds[:10]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    while True:
        print(f"\n=== PROTOCOLE DE SCAN INITIALISÉ LE {datetime.now().strftime('%d/%m %H:%M')} ===")
        j = scan_jetfly()
        p = scan_pcc()
        c = scan_chalair()
        o = scan_oyonnair()
        pan = scan_pan_european()
        cl = scan_clair_group()
        
        send_to_discord(j, p, c, o, pan, cl)
        print(f"Procédure terminée. Attente 24h.")
        time.sleep(CHECK_INTERVAL)