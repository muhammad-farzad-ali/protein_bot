# Protein Price Bot

Checks the prices of several protein powders (2–2.7 kg sizes) and posts a
report to a Discord channel, sorted from lowest to highest price per kg.

## Tracked products

| Brand | Product | Size |
|-------|---------|------|
| Bulk | Pure Whey Protein | 2.5 kg |
| MyProtein | Impact Whey Protein | 2.7 kg |
| HSN | EvoWhey Protein | 2 kg |
| ESN | Basic Whey | 2 kg |
| PBN | PBN Whey Protein | 2.27 kg |
| Optimum Nutrition | Gold Standard 100% Whey | 2.27 kg |

Current results and how each price was obtained: [PRICE_CHECKS.md](PRICE_CHECKS.md).

## Requirements

- Python 3.10+
- No third-party packages (standard library only)

## Setup

Create a `.env` file next to `check_prices.py`:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

`.env` is gitignored. Alternatively, export `DISCORD_WEBHOOK_URL` in the
environment.

## Usage

```bash
python3 check_prices.py                 # fetch prices and send to Discord
python3 check_prices.py --dry-run       # print the report only
python3 check_prices.py --changes-only  # send only when a price changed/failed
python3 check_prices.py --webhook URL   # override the webhook
```

The report shows the original price, the current sale price, savings, price per
kg, availability, and price change versus the previous run. Results are sorted
by €/kg (lowest first).

## Scheduling

Installed in the user crontab, twice daily at 09:00 and 21:00 local time:

```cron
0 9 * * * cd /home/itachi/IdeaProjects/protein_bot && /usr/bin/python3 check_prices.py >> /home/itachi/IdeaProjects/protein_bot/price_check.log 2>&1
0 21 * * * cd /home/itachi/IdeaProjects/protein_bot && /usr/bin/python3 check_prices.py >> /home/itachi/IdeaProjects/protein_bot/price_check.log 2>&1
```

Manage with `crontab -l` / `crontab -e`. Logs go to `price_check.log`.

## Notes

- Prices are point-in-time and may change; Amazon and retailer offers vary.
- HSN and ESN pages are fetched through the `r.jina.ai` reader proxy because
  direct requests are blocked or JS-heavy.
- Do not commit `.env`; rotate the Discord webhook if it is exposed.
