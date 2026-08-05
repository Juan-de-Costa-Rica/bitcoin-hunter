# Taking the puzzle-71 live page public (tier 3)

Status: **not done, deliberately.** Juan deferred this on 2026-08-05. The page
runs at tier 2 only: `https://web.mink-gopher.ts.net/puzzle71-live/`, reachable
over Tailscale. This file is the decision record so the next pass does not have
to re-derive it.

---

## 1. The one rule that shapes everything

**Selling a chance at the prize is a lottery.** In the US, the EU, and Costa
Rica, taking money in exchange for a shot at the 7.1 BTC needs gambling
licensing per jurisdiction, and crypto payments add money-transmitter rules on
top. It also cannot be made trustworthy by construction: a win materialises as
a private key on a machine we control, so no contract or escrow can guarantee
a payout to anyone else.

Do not "improve" the current page into a ticket sale. If a future session is
asked to add tickets, entries, stakes, or revenue share, it should surface this
section rather than build it.

### The three coherent designs

Only these three are internally consistent. There is no fourth.

| Model | Money in | Payout promised | Payout address collected | Needs a license |
|---|---|---|---|---|
| **Gift** (what is built today) | yes | none | **no** | no |
| **Compute pool** | no | published split | yes | no |
| **Paid ranges** | yes | yes | yes | **yes** |

The payout address is the tell. Collecting one from someone who paid *is* the
entitlement, and no disclaimer elsewhere on the page survives it. Collecting one
from someone who contributed compute instead of money is fine — that is a
work-sharing agreement, not a wager.

If we ever win and want to thank people who watched, do it afterwards as an
unannounced gift. A voluntary act after the fact is not a wager. An advertised
intention to share is.

---

## 2. What tier 3 actually requires

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
   touching a fake solution file on Oracle, confirming the page goes dark, then
   removing it.

---

## 3. If donations are ever added

- Use Stripe or Buy Me a Coffee, **not** raw BTC. The processor absorbs the
  compliance surface; taking crypto directly reintroduces money-transmitter
  questions we have no reason to take on.
- Publish where the money goes (rented GPU hours) and show the burn rate. The
  honesty is the product.
- Do not promise a rate increase in exchange for a donation amount, and do not
  collect a payout address. Both edge back toward selling odds.

**Cheapest viable first step:** a plain donate button on the existing page. One
afternoon. It answers the only question that matters — whether anyone gives
anything at all — before any further build.

---

## 4. The paid-range model (Juan's design, 2026-08-05)

Recorded because the mechanic is good and should not be re-invented from
scratch. **Not built, and it is the licensed row of the table in §1.**

Shape: a donor pays $5, we rent a GPU, we search *their* named slice of the
keyspace with it, and the bet resolves within hours. If it misses, it is over.

**What it solves.** No ledger of obligations, no claims living for years, no
tracking anybody down later. That was a genuine objection to the naive
"sponsor a share" idea and this removes it cleanly.

**What it does not solve.** The legal character is untouched. Money for a chance
at a prize is a wager, and instant resolution makes it resemble a scratch card,
which is among the most tightly regulated forms.

**What it makes worse, and the fix.** Only we can see whether a donor's range
hit. They cannot verify, and on the one day it matters we would be the sole
witness to a ~$457k event with every incentive to report a miss.

> **Fix: publish every range assignment publicly *before* the search runs,
> timestamped.** The target address is already public and any sweep of it is
> permanently visible on-chain. If a win ever happened, a stranger could check
> whether the winning key falls inside a range we had already published as
> someone's. That makes our honesty auditable after the fact without anyone
> having to trust us. Build it in from the first paid range or it is worthless
> retroactively.

### What $5 buys (computed 2026-08-05, rented 4090 at ~6 Gkeys/s, 30% margin)

| GPU spot price | Compute delivered | Donor's odds |
|---|---|---|
| $0.13/hr | 27 GPU-hours | 1 in 2.0 million |
| $0.20/hr | 17.5 GPU-hours | 1 in 3.1 million |
| $0.35/hr | 10 GPU-hours | 1 in 5.5 million |

The same $5 on Powerball buys 2.5 tickets at 1 in 117 million.

- **True headline: roughly 37x better odds of winning than Powerball.**
- **True counterweight, and it must be published alongside:** the donor gets
  about 15 cents back per $5 on average. Powerball returns far more. The
  difference is prize size, not odds — $457k versus $100M+.

---

## 4b. Subscriptions (considered 2026-08-05, not built)

Juan asked whether $1–$5/month tiers would work better than one-off payments.
He also noticed it implies a different payout mechanic. It does, and that is
where it breaks.

**The value ratio does not improve.** The math is linear, so every tier and
every duration returns the same ~2.9% of money spent. Subscriptions do not make
the deal better; they only accumulate it.

What *does* improve is the headline, and honestly so — odds compound:

| Tier | 1 month | 1 year | 5 years |
|---|---|---|---|
| $1/mo | 1 in 15.6M | 1 in 1.3M | 1 in 260,000 |
| $5/mo | 1 in 3.1M | 1 in 260,000 | 1 in 52,000 |
| $20/mo | 1 in 781,000 | 1 in 65,000 | 1 in 13,000 |

"1 in 52,000 after five years" against Powerball's 1 in 292 million per ticket
is a genuinely strong line, and it is true.

### The killer is product, not law: a shared prize collapses at scale

If subscribers split the prize, then N subscribers each paying $5/mo gives:

| Subscribers | Pool wins once every | Each person's share |
|---|---|---|
| 10 | 26,000 years | $45,868 |
| 100 | 2,600 years | $4,587 |
| 1,000 | 260 years | $459 |
| 10,000 | 26 years | $46 |

Expected value per subscriber is identical in every row (~$0.15/mo) — but the
*experience* is not. At the only subscriber counts that make it a business, the
payout becomes trivial. Nobody wants to win $46 after waiting 26 years. The
7.1 BTC prize is simply too small to divide. **Any design that splits it dies
at scale.**

### Therefore: if subscriptions, keep winner-takes-all

Make a subscription a recurring purchase of *ranges*, not a share of a pool.
Each month buys the subscriber their own slice; if their slice hits, they take
the whole prize. That preserves the pre-commitment audit in §4, keeps each bet
resolving immediately, and limits the ledger to "who is currently subscribed" —
which the billing processor already tracks — instead of a permanent claims
history.

### Legally it is not an improvement, and one variant is worse

- Selling subscriptions does not soften gambling exposure. Real lotteries sell
  direct-debit subscriptions; it is a billing cycle, not a different product.
- **The pooled-and-split variant drifts from gambling law into securities law:**
  collecting money into a common enterprise and distributing proceeds is the
  shape of a collective investment scheme. Cloud-mining contracts have been
  pursued as unregistered securities offerings on exactly this reasoning. That
  is a worse regime to land in, not a better one.

### The clean version

Subscription applied to the **gift** model in §1 is just a Patreon: $1/month
supports the hunt, the supporter gets the show and a name on the page, and is
owed nothing. Predictable revenue, no payout mechanic to design, no licensing,
no dilution problem. This is the strongest form of the subscription idea and the
only one buildable today.

---

## 5. Range assignment (applies to any multi-participant version)

**Do not assign ranges to avoid duplicate work.** That problem does not exist.
At current coverage the chance two random searchers repeat each other is about
2 in a billion. Pure random wastes nothing measurable.

Assign ranges for the *product* and the *proof*: a map that fills in, a personal
slice, and a record of what each participant actually got. Random search has
nothing to display.

- **Sizing.** Hardware spans three orders of magnitude. Use 2^32 keys as the
  unit (~16 min on our CPU, under a second on a 4090) and hand out batches sized
  to the client. There are 2^38 such chunks, so the namespace never runs out and
  no dense completion map is needed.
- **Assign randomly from the unclaimed pool, never bottom-up.** The low end is
  where every default-configured searcher in the world already grinds.
- **Verification is the hard part.** A client can report "no match" without
  doing the work, which silently poisons the coverage map. The only practical
  audit is decoy chunks: occasionally issue a range containing a key we planted
  and already know. A client that reports no match on a decoy is lying or
  broken. Design it in from the start — retrofitting means discarding all
  coverage history.

### Why pool scale is not a joke

| Scale | Keyspace swept per year |
|---|---|
| Our Oracle box (~4.45 Mkeys/s) | 0.00001% |
| One rented 4090 (~6 Gkeys/s) | 0.016% |
| 100 GPUs | 1.6% |
| 1,000 GPUs | 16% |

A thousand-GPU pool has a genuine shot within a few years. This is how puzzles
#66–#70 were solved. At that scale the binding constraint is trust, not compute
— and note the custody problem simply moves: in a volunteer pool the winning key
appears on the *finder's* machine, and they can keep all of it.

---

## 6. Web3 findings (researched 2026-08-05)

Juan asked whether another chain or web3 rails would suit this better. Summary:
**keep the hunt on Bitcoin and use web3, if at all, only for payments.**

- **No Ethereum equivalent puzzle exists at meaningful scale.** The BTC puzzle
  is a 2015 one-off: 160 addresses with keys in known bit-ranges, ~1,000 BTC
  total, 79 solved. What exists on ETH instead is the Profanity vanity-address
  flaw — a real vulnerability, and draining those keys is theft. Out of scope,
  permanently.
- **No chain offers a math advantage.** Ethereum uses the same secp256k1 curve.
  Identical work per key, identical odds.
- **Bridges solve a problem we do not have.** Landscape for the record: WBTC
  (~$10B, BitGo custody), cbBTC (~$3B, Coinbase, default on Base), tBTC (~$500M,
  decentralized), plus newer BitVM2-based bridges (BOB, Citrea, Bitlayer,
  Babylon). We would never bridge a win — it adds custody risk for nothing — and
  taking donations does not require BTC on another chain.
- **MetaMask is no longer the default.** The market fragmented and embedded
  wallets are now the consumer norm: sign in with email or a passkey, wallet
  created behind the scenes, nothing to install. Stripe acquired Privy in June
  2025; MetaMask's own embedded product is the former Web3Auth. Requiring a
  browser extension today costs most casual visitors.
- **If crypto payment is wanted anyway:** accept USDC on Base via Coinbase
  Commerce. Cheap, hosted, no contract to write, and the receiving address can
  be published for transparent funding.
- **Full web3** (embedded wallets, on-chain record of sponsored ranges, token
  -gated views) is weeks of work and will not increase donations. Build it only
  if learning that stack is itself the goal.
