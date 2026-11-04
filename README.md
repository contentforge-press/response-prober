# response-prober

Measure how long small webshops take to answer **pre-sales email** — by
mystery shopping them with real, executable purchase enquiries.

Small shops lose orders not because their product is bad but because a
customer asked "do you do wholesale from 40 units?" on a Tuesday and
nobody answered until Thursday. This tool makes that visible, with a
timestamp and a quoted question.

```
pip install -r requirements.txt  # none. stdlib only.
python3 response_prober.py gen shop.json          # generate the enquiry
python3 response_prober.py scan state.json        # judge all probes
python3 response_prober.py letter state.json 26.5 # evidence letter draft
```

`shop.json`:
```json
{"name": "Kerzenmanufaktur X", "email": "info@shop.example",
 "category": "candle", "lang": "de"}
```

## How judging works

| verdict    | meaning                                              |
|------------|------------------------------------------------------|
| `answered` | shop replied — healthy support, leave them alone      |
| `hot`      | 24 h+ silence — support is leaking pre-sales revenue  |
| `waiting`  | under 24 h, still counting                            |

## Ethics (hard rules)

- Enquiries are **real questions** a buyer would actually ask (quantity, lead time, price) — never fake orders, never fake urgency, never impersonating an institution.
- If the shop answers, you continue the conversation honestly.
- The evidence letter **discloses** that the enquiry was a test.
- Volume stays human-scale: a handful of shops, not a spray.

MIT. Check your local anti-spam rules before sending; you own your sending domain's reputation.

## See also

A hosted, merchant-friendly version of the same idea (the shop checks
*itself*) lives at `check.pixharvest.com` — free support audit for
EU small shops.

## Don't want to run it yourself?

Two managed options:

- **Free shop health-check (DE/NL):** submit your shop at
  [check.pixharvest.com](https://check.pixharvest.com) — you get a report of
  your response times and unanswered pre-sales questions within 24 h.
- **Shop-Support (managed inbox):** if your shop is leaking pre-sales email,
  [pixharvest.com](https://pixharvest.com) runs the answers for you — AI drafts
  from your own templates, sensitive cases get a 1-click human approval,
  flat €49/week.

Shops that answer fast can claim a **response badge** for their footer
(see [leaderboard](https://check.pixharvest.com/leaderboard)).
