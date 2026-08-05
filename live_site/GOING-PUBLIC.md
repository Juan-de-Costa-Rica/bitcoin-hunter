# Puzzle-71 hunt: public deployment and paid-product design

Two things live here:

- **Part A** — what it takes to put the existing live page on the public
  internet. Deferred by Juan on 2026-08-05; the page runs at tier 2 only,
  `https://web.mink-gopher.ts.net/puzzle71-live/`, reachable over Tailscale.
- **Part B** — a design thought experiment: if we sold hunting to the public,
  what is the right product? Not built. Explored with Juan on 2026-08-05.

## Operating premise for Part B

**Assume a jurisdiction where running a lottery is permitted and licensed.**
Juan set this premise deliberately on 2026-08-05: legality is not the question
being explored, so it is not re-argued in every section. Everything in Part B is
a *design* argument — what makes a good product, what breaks at scale, what the
numbers actually are. Licensing facts are parked in Appendix L.

Because that premise is doing real work, state it plainly to anyone who picks
this up later: **nothing in Part B is buildable in Costa Rica as written.** See
Appendix L before anyone treats it as a plan rather than a design study.

---

# Part A — taking the live page public (tier 3)

1. **Pick the hostname.** Suggest a subdomain of jonjuan.com. DNS for that zone
   is Cloudflare, proxied — Namecheap is hosting only. See the
   `jonjuan_dns_cloudflare` and `public_access_oracle_caddy` memories.
2. **Add the Caddy route on Oracle.** The real file is `~/caddy/Caddyfile` on
   the Oracle box. Route the new host to the homelab web container over
   Tailscale, same shape as the existing shared routes. Juan approves before any
   public bind — this is a consent boundary.
3. **Decide the gate.** Existing public routes use a key/cookie gate (mistaway
   does). This page is meant to be seen, so it would be the first ungated one.
   Confirm that with Juan explicitly rather than assuming.
4. **Rate-limit and cache.** `data.json` is refreshed every 10 minutes by the
   isocrono rail `puzzle71-live-refresh`; the page polls it every 60s. Public
   traffic should hit a Caddy cache, not the homelab container, and must never
   cause an extra ssh to Oracle — the collector is the only thing that talks to
   the hunt box, on its own schedule.
5. **Verify the kill switch before launch.** `bin/refresh-puzzle71-live-data.sh`
   publishes a dark feed the moment a `SOLUTION_puzzle71_*.txt` exists on
   Oracle. Public exposure makes this critical, not optional: a page announcing
   a solve hands snipers the pubkey window before the private-relay sweep in
   `../keyhunt_runner/SOLUTION-RUNBOOK.md`. Test by touching a fake solution
   file on Oracle, confirming the page goes dark, then removing it.

This step-5 requirement survives every design in Part B. Anything public that
reveals a solve in real time destroys the prize it is advertising.

---

# Part B — the paid-hunt product

## B1. The shape that works

Of the structures considered, one survives scrutiny:

> **Sell a named slice of the keyspace. Winner takes the whole prize. Publish
> every assignment before it is searched. Resolve within hours.**

A buyer pays, we rent GPU time, we search *their* slice, and it is over the same
day. Why each part matters:

- **Named slice, not a share of a pool.** The prize is too small to divide (§B3).
- **Winner takes all.** Preserves a life-changing outcome at any scale.
- **Published in advance.** Makes our honesty auditable (§B2).
- **Immediate resolution.** No claims ledger, nobody to track down years later.
  This was Juan's contribution and it removes a genuine operational problem:
  bets settle same-day, so the only records needed are billing records.

## B2. The trust problem, and the fix

Only we can see whether a buyer's slice hit. They cannot verify it, and on the
one day it matters we would be the sole witness to a ~$459k event with every
incentive to report a miss. Unfixed, this is the flaw that sinks the product —
it is exactly the pattern that made every crypto-lottery scam.

> **Fix: publish each range assignment publicly *before* searching it,
> timestamped.** The target address is already public and any sweep of it is
> permanently visible on-chain. If a win ever happened, a stranger could check
> whether the winning key falls inside a range already published as someone's.
> Honesty becomes auditable after the fact, by anyone, with no trust in us.

Build this from the first paid range. It cannot be added retroactively — the
whole value is that the commitment predates the result.

## B3. Never split the prize

If buyers share the jackpot, the product dies precisely when it succeeds. N
subscribers at $5/month, split evenly:

| Buyers | Pool wins once every | Each person's share |
|---|---|---|
| 10 | 26,000 years | $45,868 |
| 100 | 2,600 years | $4,587 |
| 1,000 | 260 years | $459 |
| 10,000 | 26 years | $46 |

Expected value per person is identical in every row (~$0.15/mo). The
*experience* is not. At the subscriber counts that make this a business, the
payout is trivial — nobody waits 26 years to win $46. 7.1 BTC cannot be
meaningfully divided. Every design that splits it fails.

## B4. The binding constraint is return-to-player, not odds

This is the real problem, and it only becomes visible once legality is set
aside.

What $5 buys at a $0.20/hr rented 4090 (~6 Gkeys/s), 30% margin:

| GPU spot price | Compute delivered | Buyer's odds |
|---|---|---|
| $0.13/hr | 27 GPU-hours | 1 in 2.0 million |
| $0.20/hr | 17.5 GPU-hours | 1 in 3.1 million |
| $0.35/hr | 10 GPU-hours | 1 in 5.5 million |

The same $5 on Powerball buys 2.5 tickets at 1 in 117 million, so **the odds
headline is genuinely excellent: ~37x better than Powerball, and true.**

But the money coming back is not:

- This product, jackpot only: **~2.9% of money spent**, and only ~6.5% even at
  zero margin.
- State lotteries: ~50% across all prize tiers.
- Slot machines: 85–95%.

The cause is prize size, not odds — $459k against Powerball's $100M+. And it
cannot be fixed by trimming margin. **A 3% return-to-player game gets played
once, never twice.** Any real version of this must solve B5.

Note on target choice: #71 is already the best available. Puzzle prizes grow
linearly with number (N/10 BTC) while keyspace doubles each step, so every
higher puzzle is worse value per key, and all lower ones are solved.

## B5. Near-miss prize tiers — the design that makes it viable

The jackpot cannot carry the product, so manufacture intermediate prizes out of
work already being done.

The search computes a hash160 for every key it tries. Comparing the *first k
bits* of that hash against the target's is a mask-and-compare on a value already
in a register — **detection is essentially free.** Near-misses are common and
tunable: pick k, get any frequency you want.

Example ladder for a $5 purchase with 20% of revenue going to compute
(1.08 × 10^14 keys):

| Tier | Frequency | Pays | EV |
|---|---|---|---|
| 44-bit prefix match | 6.1 times per purchase | $0.10 | $0.61 |
| 50-bit | 1 in 10 purchases | $4.00 | $0.38 |
| 56-bit | 1 in 667 purchases | $300 | $0.45 |
| 62-bit | 1 in 42,701 purchases | $15,000 | $0.35 |
| Full key (jackpot) | 1 in 10.9 million purchases | $458,681 | $0.04 |

Total return-to-player: **37%**, leaving ~43% margin after compute. Every number
above is a free parameter — move the bit widths and payouts to hit whatever RTP
and margin the business wants.

What this buys, beyond the RTP number:

- **Something happens every single purchase.** A 44-bit hit lands six times per
  $5. The screen is never dead.
- **A real prize ladder**, so the product resembles a scratch card rather than a
  coin flip against a wall.
- **Verifiable wins.** Every tier is checkable by anyone: hash the reported key,
  compare the prefix. Unlike the jackpot, near-miss wins prove themselves
  instantly and publicly. That is a trust asset, not just a prize.

Use bit prefixes, not byte prefixes. Bytes jump by 256x per step and give no
usable control; bits let you place each tier exactly.

## B6. Subscriptions

The value ratio is linear, so every tier and duration returns the same
percentage. Subscriptions do not improve the deal; they accumulate it. What
improves is the headline, honestly:

| Tier | 1 month | 1 year | 5 years |
|---|---|---|---|
| $1/mo | 1 in 15.6M | 1 in 1.3M | 1 in 260,000 |
| $5/mo | 1 in 3.1M | 1 in 260,000 | 1 in 52,000 |
| $20/mo | 1 in 781,000 | 1 in 65,000 | 1 in 13,000 |

"1 in 52,000 after five years" against Powerball's 1 in 292 million is a strong,
true line.

Implement a subscription as a **recurring purchase of ranges**, never as
membership in a shared pool (§B3). That keeps winner-takes-all, keeps
resolution same-day, and limits records to "who is subscribed now" — which the
payment processor already tracks.

## B7. Range assignment

**Do not assign ranges to avoid duplicate work.** That problem does not exist:
at current coverage, the chance two random searchers repeat each other is about
2 in a billion. Random search wastes nothing measurable.

Assign ranges for the product and the proof — a map that fills in, a personal
slice, and a record of who got what.

- **Sizing.** Hardware spans three orders of magnitude. Use 2^32 keys as the
  unit (~16 min on our Oracle CPU, under a second on a 4090) and hand out
  batches sized to the client. There are 2^38 such chunks; the namespace never
  runs out and no dense completion map is needed.
- **Assign randomly from the unclaimed pool, never bottom-up.** The low end is
  where every default-configured searcher in the world already grinds.
- **If third parties ever run the search** (a volunteer pool rather than our
  rented GPUs), verification becomes the hard part: a client can report "no
  match" without doing the work, silently poisoning the coverage map. The only
  practical audit is decoy ranges containing a key we planted and already know.
  Design it in from the start; retrofitting means discarding all coverage
  history. Note also that a volunteer pool moves the custody problem rather than
  solving it — the winning key appears on the finder's machine, and they can
  simply keep it.

## B8. Why pool scale is not a joke

| Scale | Keyspace swept per year |
|---|---|
| Our Oracle box (~4.45 Mkeys/s) | 0.00001% |
| One rented 4090 (~6 Gkeys/s) | 0.016% |
| 100 GPUs | 1.6% |
| 1,000 GPUs | 16% |

A thousand-GPU operation has a genuine shot within a few years, which is how
puzzles #66–#70 were solved. At that scale compute stops being the constraint.

## B9. Payments and web3 (researched 2026-08-05)

**Keep the hunt on Bitcoin; use web3, if at all, only for payments.**

- **No Ethereum equivalent puzzle exists at meaningful scale.** The BTC puzzle
  is a 2015 one-off: 160 addresses with keys in known bit-ranges, ~1,000 BTC
  total, 79 solved. What exists on ETH instead is the Profanity vanity-address
  flaw — a real vulnerability, and draining those keys is theft. Out of scope
  permanently, premise or no premise.
- **No chain offers a math advantage.** Ethereum uses the same secp256k1 curve.
  Identical work per key, identical odds.
- **Bridges solve a problem we do not have.** For the record: WBTC (~$10B, BitGo
  custody), cbBTC (~$3B, Coinbase, default on Base), tBTC (~$500M,
  decentralized), plus newer BitVM2-based bridges (BOB, Citrea, Bitlayer,
  Babylon). We would never bridge a win — custody risk for no benefit — and
  taking payments does not require BTC on another chain.
- **MetaMask is no longer the default.** The market fragmented and embedded
  wallets are the consumer norm: sign in with email or passkey, wallet created
  behind the scenes, nothing to install. Stripe acquired Privy in June 2025;
  MetaMask's own embedded product is the former Web3Auth. Requiring a browser
  extension today costs most casual visitors.
- **Simplest crypto path:** accept USDC on Base via Coinbase Commerce. Cheap,
  hosted, no contract to write, and the receiving address can be published so
  funding is transparent.
- **Full web3** (embedded wallets, on-chain range registry, token-gated views)
  is weeks of work and will not increase revenue. Build it only if learning that
  stack is the point. One genuine exception: an on-chain range registry is a
  natural fit for the §B2 pre-commitment, since it timestamps assignments
  publicly and immutably without us running anything.

---

# Appendix L — licensing facts (parked, not argued)

Recorded once so the premise is honest about what it assumes.

- Money for a chance at a prize is a lottery in most jurisdictions, including
  the US and EU. Instant resolution makes it resemble a scratch card, among the
  most tightly regulated forms.
- **A pooled-and-split design is a different and worse problem:** collecting
  money into a common enterprise and distributing proceeds is the shape of a
  collective investment scheme. Cloud-mining contracts have been pursued as
  unregistered securities on exactly that reasoning. §B3 rejects splitting on
  product grounds anyway.
- **Costa Rica does not issue gambling licences** (checked 2026-08-05). Operators
  incorporate locally (SRL/SA) with a *data processing licence*, hold the actual
  gaming licence abroad, and must block Costa Rican residents from playing. So
  "run it from home" is not available: the operating base could sit in Costa
  Rica, but the licence and the wagering must sit elsewhere, and Juan's own
  country would be geo-blocked from his own product.
- The zero-exposure version remains available and needs no premise at all: take
  donations as gifts with no payout claim, collect no payout address, promise
  nothing. That is what the live page does today, and a $1/month version of it
  is simply a Patreon.
