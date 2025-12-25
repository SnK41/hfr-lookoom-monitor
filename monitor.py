import json
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATE_FILE = Path("state.json")

# IMPORTANT: adapte le pseudo ici si besoin (casse incluse)
PSEUDO = "LooKooM"

SEARCH_URL = (
    "https://forum.hardware.fr/forum1.php?"
    "config=hfr.inc&cat=1&recherches=1&resSearch=200&"
    "titre=3&search=&pseud=" + PSEUDO + "&daterange=2&searchtype=1&searchall=1"
)

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"seen": []}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def fetch_topic_links():
    r = requests.get(SEARCH_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    topics = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        txt = a.get_text(strip=True)
        if "sujet_" in href and href.endswith(".htm") and txt:
            url = href if href.startswith("http") else "https://forum.hardware.fr" + href
            topics.append((txt, url))

    # dédoublonnage
    dedup = {}
    for title, url in topics:
        dedup[url] = title
    return [(title, url) for url, title in dedup.items()]

def send_email(subject, body):
    smtp_host = "smtp.gmail.com"
    smtp_port = 587

    smtp_user =  os.environ["SMTP_USER"]
    smtp_pass =  os.environ["SMTP_PASS"]
    to_addr   =  os.environ["MAIL_TO"]
    from_addr =  os.environ.get("MAIL_FROM", smtp_user)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    with smtplib.SMTP(smtp_host, smtp_port) as s:
        s.starttls()
        s.login(smtp_user, smtp_pass)
        s.send_message(msg)

def main():
    state = load_state()
    seen = set(state["seen"])

    current = fetch_topic_links()
    new_topics = [(t, u) for (t, u) in current if u not in seen]

    if new_topics:
        lines = [f"Nouveaux topics où {PSEUDO} a posté depuis le dernier relevé:\n"]
        for title, url in new_topics:
            lines.append(f"- {title}\n  {url}")
        body = "\n".join(lines)
        send_email(f"[HFR] Nouveaux posts de {PSEUDO}", body)

        state["seen"] = list(seen.union({u for _, u in new_topics}))
        save_state(state)
    else:
        # pas d’email si rien de nouveau
        pass

if __name__ == "__main__":
    import os
    main()
          - name: Persist state.json
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"
          git add state.json || true
          git commit -m "Update HFR monitor state" || true
          git push || true

