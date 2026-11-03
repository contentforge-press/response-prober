#!/usr/bin/env python3
"""response_prober.py -- measure how long small webshops take to answer
pre-sales email, by mystery shopping them.

What it does
------------
1. Generate a real, executable purchase enquiry (per product category,
   per language) and send it from a neutral alias.
2. Time the reply. Answered within 24 h = healthy. Silent for 24 h =
   "hot": this shop's customer service is leaking pre-sales revenue.
3. Build an evidence letter that quotes the original question and the
   elapsed hours -- and is honest that the enquiry was a test.

Why: on small shops, unanswered pre-sales mail is the single most
visible support failure, and "I asked you on Tuesday and heard nothing"
converts an order of magnitude better than generic pitching.

Ethics (hard rules, do not remove):
  - enquiries must be genuinely executable (real question, real quantity)
  - no impersonating institutions, no fabricated urgency
  - if the shop answers, continue the conversation honestly
  - the evidence letter discloses that the enquiry was a test

Usage:
  python3 response_prober.py gen shop.json          # print next enquiry
  python3 response_prober.py scan state.json        # judge all probes
  python3 response_prober.py letter state.json 26.5 # draft evidence mail

state.json: {"probes": [{"shop": "shop.example", "name": "Shop",
            "category": "candle", "lang": "de", "sent_at": "..."}]}

MIT license. You are responsible for complying with anti-spam law in
your jurisdiction (double opt-in does not apply to B2B enquiry replies,
but volume limits and honest identification are on you).
"""
import json
import sys
from datetime import datetime, timezone

HOT_AFTER_H = 24

# Real, executable purchase enquiries per category. Specific enough to quote.
PROBES = {
    "candle": {
        "de": ("Großhandelsanfrage Kerzen",
               "Guten Tag,\n\nich suche für unser Boutique-Hotel in "
               "München ca. 40 Kerzen als Zimmer-Ausstattung, gerne "
               "wiederkehrend.\n\nGibt es bei Ihnen einen "
               "Großhandelspreis ab 40 Stück, und wie lange wäre die "
               "Lieferzeit?\n\nViele Grüße\n{alias}"),
        "nl": ("Groothandelsvraag kaarsen",
               "Goedemiddag,\n\nik zoek voor ons boutiquehotel ca. 40 "
               "kaarsen als kamervulling, liefst structureel.\n\nIs er "
               "een groothandelsprijs vanaf 40 stuks en wat is de "
               "levertijd?\n\nMet vriendelijke groet\n{alias}"),
        "en": ("Wholesale enquiry: candles",
               "Hello,\n\nI'm looking for around 40 candles as room "
               "amenities for a boutique hotel, ideally on a recurring "
               "basis.\n\nDo you offer wholesale pricing from 40 units, "
               "and what would the lead time be?\n\nBest regards\n{alias}"),
    },
    "coffee": {
        "de": ("Anfrage Kaffee für Büro",
               "Guten Tag,\n\nwir suchen für unser Büro in Berlin "
               "regelmäßig Bohnen (ca. 5 kg/Monat), am besten "
               "mittelgeröstet.\n\nMacht ihr so ein Abo mit "
               "Firmenrabatt?\n\nViele Grüße\n{alias}"),
        "nl": ("Vraag koffie voor kantoor",
               "Goedemiddag,\n\nwij zoeken voor ons kantoor regelmatig "
               "bonen (ca. 5 kg/maand), het liefst middengebrand.\n\n"
               "Doen jullie zo'n abonnement met korting?\n\n"
               "Met vriendelijke groet\n{alias}"),
        "en": ("Office coffee enquiry",
               "Hello,\n\nour Berlin office needs coffee beans regularly "
               "(about 5 kg/month), medium roast preferred.\n\nDo you do "
               "a subscription with a business discount?\n\n"
               "Best regards\n{alias}"),
    },
    "jewelry": {
        "de": ("Anfrage personalisierte Ringe",
               "Guten Tag,\n\nich suche für unsere Hochzeit im Mai 8 "
               "personalisierte Ringe (Gravur der Namen).\n\nMacht ihr "
               "so eine Kleinserie, und wie lange braucht ihr?\n\n"
               "Viele Grüße\n{alias}"),
        "nl": ("Vraag gegraveerde ringen",
               "Goedemiddag,\n\nik zoek voor onze bruiloft in mei 8 "
               "gegraveerde ringen (namen erin).\n\nKunnen jullie zo'n "
               "kleine serie maken, en hoe lang duurt dat?\n\n"
               "Met vriendelijke groet\n{alias}"),
        "en": ("Personalised rings enquiry",
               "Hello,\n\nfor a May wedding I'm looking for 8 "
               "personalised rings (engraved names).\n\nDo you take on "
               "small runs like that, and what is your turnaround?\n\n"
               "Best regards\n{alias}"),
    },
}
FALLBACK = {
    "de": ("Anfrage Kleinserie",
           "Guten Tag,\n\nich hätte eine Frage zu einer Kleinserie "
           "(ca. 30 Stück) – macht ihr sowas, und was würde das "
           "kosten?\n\nViele Grüße\n{alias}"),
    "nl": ("Vraag kleine serie",
           "Goedemiddag,\n\nik heb een vraag over een kleine serie "
           "(ca. 30 stuks) – kunnen jullie dat, en wat zou het "
           "kosten?\n\nMet vriendelijke groet\n{alias}"),
    "en": ("Small batch enquiry",
           "Hello,\n\na question about a small batch (about 30 units) "
           "– is that something you do, and what would it cost?\n\n"
           "Best regards\n{alias}"),
}

# Neutral aliases (standard mystery-shopping practice: a plausible
# customer name, never an institution, never a fake emergency).
ALIASES = {
    "de": ["Max Berger", "Lena Hartmann", "Jonas Krüger"],
    "nl": ["Daan de Vries", "Sanne Bakker", "Joris Meijer"],
    "en": ["Tom Ellis", "Mara Quinn", "Ben Adler"],
}


def gen_probe(shop):
    """Return (subject, body, alias) for shop: {name, category, lang}."""
    lang = shop.get("lang", "de")
    tpl = PROBES.get(shop.get("category", ""), {}).get(lang) or FALLBACK[lang]
    pool = ALIASES[lang]
    alias = pool[abs(hash(shop.get("name", "x"))) % len(pool)]
    return tpl[0], tpl[1].format(alias=alias), alias


def check_probe(probe, now, replies):
    """probe: {shop, sent_at}. replies: iterable of answering addresses.
    Match on the domain part. Returns waiting / hot / answered."""
    domain = probe.get("shop", "").lower().lstrip("@")
    for addr in replies:
        local, _, dom = str(addr).lower().partition("@")
        if dom == domain or (not dom and local == domain):
            return "answered"
    sent = datetime.fromisoformat(probe["sent_at"].replace("Z", "+00:00"))
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    hours = (now - sent).total_seconds() / 3600
    return "hot" if hours >= HOT_AFTER_H else "waiting"


def evidence_letter(shop, probe_hours, probe_quote, offer):
    """Draft the evidence letter for a 'hot' shop. Quotes the original
    question and the elapsed hours, and discloses the test. `offer` is
    your one-paragraph pitch (what you do and how to start)."""
    lang = shop.get("lang", "de")
    if lang == "nl":
        head = ("Mijn testvraag van dinsdag - {h} uur later\n\n"
                "{greeting},\n\nop dinsdag stuurden wij een testvraag "
                "(onder een andere naam) met de letterlijke vraag: "
                "\"{q}\"\n\nNa {h} uur kwam er nog geen antwoord - geen "
                "verwijt, dit is de realiteit van kleine shops: mails "
                "komen binnen terwijl je aan het verpakken bent.\n\n")
        sign = "\nMet vriendelijke groet"
    elif lang == "en":
        head = ("Our test question from Tuesday - {h} hours later\n\n"
                "{greeting},\n\non Tuesday we sent a test enquiry (under "
                "another name) with the literal question: \"{q}\"\n\n"
                "After {h} hours there was still no answer - no blame, "
                "that is the reality of small shops: mail arrives while "
                "you are packing boxes.\n\n")
        sign = "\nBest regards"
    else:
        head = ("Unsere Testfrage von Dienstag - {h} Stunden spaeter\n\n"
                "{greeting},\n\nam Dienstag schickten wir eine "
                "Testanfrage (unter anderem Namen) mit der woertlichen "
                "Frage: \"{q}\"\n\nNach {h} Stunden ist noch keine "
                "Antwort gekommen - kein Vorwurf, das ist der Alltag "
                "kleiner Shops: Mails kommen rein, waehrend man gerade "
                "verpackt.\n\n")
        sign = "\nFreundliche Gruesse"
    return (head + offer + sign).format(
        h=probe_hours, greeting=shop.get("greeting", "Hallo"),
        q=probe_quote)


def load_state(path):
    try:
        return json.load(open(path))
    except FileNotFoundError:
        return {"probes": []}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    now = datetime.now(timezone.utc)
    if cmd == "gen":
        shop = json.load(open(sys.argv[2]))
        s, b, a = gen_probe(shop)
        print("TO: %s\nFROM: <your alias mailbox>\nSUBJECT: %s\nALIAS: %s\n\n%s"
              % (shop.get("email", "?"), s, a, b))
    elif cmd == "letter":
        state = load_state(sys.argv[2])
        hours = float(sys.argv[3])
        offer = sys.argv[4] if len(sys.argv) > 4 else "[your one-paragraph offer]"
        for p in state.get("probes", []):
            if p.get("status") == "hot":
                print(evidence_letter(p, hours, p.get("quote", "..."), offer))
                break
    else:  # scan
        state = load_state(sys.argv[2] if len(sys.argv) > 2 else "state.json")
        for p in state.get("probes", []):
            p["status"] = check_probe(p, now, set())
            print("%-40s %s" % (p.get("shop"), p["status"]))


if __name__ == "__main__":
    main()
