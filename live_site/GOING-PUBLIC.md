# Taking the puzzle-71 live page public (tier 3)

Status: **not done, deliberately.** Juan deferred this on 2026-08-05. The page
runs at tier 2 only: `https://web.mink-gopher.ts.net/puzzle71-live/`, reachable
over Tailscale. This file is the decision record so the next pass does not have
to re-derive it.

## The one rule that shapes everything

**It never sells a chance at the prize.** Taking money in exchange for a shot at
the 7.1 BTC is a lottery in the US, the EU, and Costa Rica — it needs gambling
licensing per jurisdiction, and adding crypto payments pulls in money-transmitter
rules on top. Worse, it cannot be made trustworthy: a win materialises as a
private key on a machine we control, so no contract or escrow can guarantee a
payout to anyone else. Every "improvement" toward tickets, entries, stakes,
odds-for-sale, or revenue share is off the table, not merely risky.

What is allowed: donations framed as gifts with **no** prize entitlement, stated
in plain language on the page (Twitch-subscription shape — money for
entertainment, no wager). Any donation copy must say the donor receives nothing
if the key is found.

## What tier 3 actually requires

1. **Pick the hostname.** Suggest a subdomain of jonjuan.com. DNS for that zone
   is Cloudflare, proxied — Namecheap is hosting only. See the
   `jonjuan_dns_cloudflare` and `public_access_oracle_caddy` memories.
2. **Add the Caddy route on Oracle.** The real file is `~/caddy/Caddyfile` on the
   Oracle box. Route the new host to the homelab web container over Tailscale,
   same shape as the existing shared routes. Juan approves before any public
   bind — this is a consent boundary.
3. **Decide the gate.** Existing public routes use a key/cookie gate
   (mistaway does). This page is meant to be seen, so it would be the first
   ungated one. Confirm that with Juan explicitly rather than assuming.
4. **Rate-limit and cache.** `data.json` is refreshed every 10 minutes by the
   isocrono rail `puzzle71-live-refresh`; the page polls it every 60s. Public
   traffic should hit a Caddy cache, not the homelab container, and must never
   cause an extra ssh to Oracle — the collector is the only thing that talks to
   the hunt box, on its own schedule.
5. **Keep the kill switch verified.** `bin/refresh-puzzle71-live-data.sh`
   publishes a dark feed the moment a `SOLUTION_puzzle71_*.txt` exists on
   Oracle. Public exposure makes this critical, not optional: a page announcing
   a solve hands snipers the pubkey window before the private-relay sweep in
   `../keyhunt_runner/SOLUTION-RUNBOOK.md`. Test it before going public by
   touching a fake solution file on Oracle and confirming the page goes dark,
   then removing it.

## If donations are ever added

- Use Stripe or Buy Me a Coffee, **not** raw BTC. The processor absorbs the
  compliance surface; taking crypto directly reintroduces money-transmitter
  questions we have no reason to take on.
- Publish where the money goes (rented GPU hours) and show the burn rate. The
  honesty is the product.
- Do not promise a rate increase in exchange for a donation amount. That edges
  back toward selling odds.

## Rented-GPU note

If donations ever fund rented GPUs, the numbers were worked out on 2026-08-05: a
rented RTX 4090 runs KeyHunt-Cuda at roughly 6 Gkeys/s, about 1,350x the Oracle
box, at $0.13–0.35/hr on gpus.io. That is ~2.4 cents per Powerball-ticket's
worth of odds versus $2 at a gas station — but the prize is only ~$457k, so the
expected return is about 6 cents per dollar spent. It is entertainment, not an
investment, and the page must keep saying so.
