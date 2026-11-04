#!/usr/bin/env python3
"""
Prati "Informacije uživo" sa sajta Srbijavoza i šalje Telegram poruku
kada se pojavi obaveštenje koje se tiče relacije Pančevo – Zemun.

Izvor: WordPress REST API koji puni stranicu srbijavoz.rs/informacije/
Stanje (već poslata obaveštenja) čuva se u seen.json.
"""

import html
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_URL = "https://www.srbvoz.rs/wp-json/wp/v2/info_post?per_page=50"
STATE_FILE = Path(__file__).with_name("seen.json")

# Obaveštenja starija od ovoga se ignorišu (štiti od slanja stare istorije
# i od obaveštenja koja su samo naknadno izmenjena).
MAX_AGE_HOURS = int(os.environ.get("MAX_AGE_HOURS", "24"))

# Ključne reči (bez dijakritika, mala slova). Može se pregaziti promenljivom
# KEYWORDS_REGEX u GitHub podešavanjima, bez menjanja koda.
#  - pancev(o|a|u|om)  -> Pančevo, ali NE "Pančevački most" (to je druga priča)
#  - vojlovic          -> Pančevo Vojlovica
#  - vrsac/vrsca       -> vozovi Vršac–Zemun prolaze kroz Pančevo
#  - obustav... svih   -> opšte obustave celog saobraćaja
DEFAULT_KEYWORDS = (
    r"\bpancev(o|a|u|om)\b"
    r"|vojlovic"
    r"|\bvrs(ac|ca|cu)\b"
    r"|obustav\w*\s+(\w+\s+){0,3}(svih|sav|celokupn)"
    r"|(svih|svi)\s+(medjugradskih\s+|putnickih\s+)?vozova\s+(\w+\s+){0,3}(nece|obustav)"
)
KEYWORDS = re.compile(os.environ.get("KEYWORDS_REGEX") or DEFAULT_KEYWORDS)

TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")

CYR = dict(zip(
    "абвгдђежзијклљмнњопрстћуфхцчџш",
    ["a", "b", "v", "g", "d", "dj", "e", "z", "z", "i", "j", "k", "l", "lj",
     "m", "n", "nj", "o", "p", "r", "s", "t", "c", "u", "f", "h", "c", "c",
     "dz", "s"],
))


def normalize(text: str) -> str:
    """Mala slova, ćirilica -> latinica, bez dijakritika (š->s, đ->dj...)."""
    text = text.lower().replace("đ", "dj")
    text = "".join(CYR.get(ch, ch) for ch in text)
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def strip_html(raw: str) -> str:
    raw = re.sub(r"<br\s*/?>|</p>", "\n", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\xa0]+", " ", raw)
    return re.sub(r"\n\s*\n+", "\n", raw).strip()


def fetch_notices():
    req = urllib.request.Request(API_URL, headers={
        "User-Agent": "Mozilla/5.0 (bg-voz-alert; personal notifier)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"sent": []}


def save_state(state):
    state["sent"] = state["sent"][-300:]  # dovoljno za istoriju, fajl ostaje mali
    STATE_FILE.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")


def send_telegram(text: str):
    data = urllib.parse.urlencode({
        "chat_id": TG_CHAT,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    with urllib.request.urlopen(url, data=data, timeout=30) as resp:
        resp.read()


def format_message(post) -> str:
    title = html.unescape(post["title"]["rendered"])
    body = strip_html(post["content"]["rendered"])
    if len(body) > 3000:
        body = body[:3000].rsplit(" ", 1)[0] + " …"
    when = post["date"].replace("T", " ")[:16]
    return (
        f"🚆 <b>{html.escape(title)}</b>\n"
        f"<i>{when}</i>\n\n"
        f"{html.escape(body)}\n\n"
        f'<a href="{html.escape(post["link"])}">Otvori na sajtu</a>'
    )


def main():
    dry_run = "--dry-run" in sys.argv
    if not dry_run and not (TG_TOKEN and TG_CHAT):
        sys.exit("Nedostaju TELEGRAM_BOT_TOKEN i/ili TELEGRAM_CHAT_ID.")

    state = load_state()
    sent = set(state["sent"])
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)

    try:
        posts = fetch_notices()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        # Kratki ispad sajta ne treba da obori workflow svakih 15 minuta.
        print(f"Upozorenje: ne mogu da preuzmem obaveštenja ({e}).")
        return

    new_matches = []
    for post in sorted(posts, key=lambda p: p["date_gmt"]):
        if post["id"] in sent:
            continue
        published = datetime.fromisoformat(post["date_gmt"]).replace(tzinfo=timezone.utc)
        if published < cutoff:
            continue
        haystack = normalize(
            post["title"]["rendered"] + " " + strip_html(post["content"]["rendered"])
        )
        if KEYWORDS.search(haystack):
            new_matches.append(post)

    print(f"Preuzeto {len(posts)} obaveštenja, novih za tvoju liniju: {len(new_matches)}.")

    for post in new_matches:
        msg = format_message(post)
        if dry_run:
            print("-" * 60 + "\n" + msg)
        else:
            send_telegram(msg)
            state["sent"].append(post["id"])

    if new_matches and not dry_run:
        save_state(state)


if __name__ == "__main__":
    main()
