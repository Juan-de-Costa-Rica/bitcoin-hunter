# Puzzle #71 Solution Runbook — anti-sniping procedure

**Read this BEFORE touching the key. The key is radioactive until step 6.**

## Threat model (why this document exists)

The puzzle address `1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU` is P2PKH: the chain
only knows the *hash* of the public key. The moment a spend transaction is
broadcast, the transaction reveals the full public key. With the pubkey known,
recovering a private key confined to a 71-bit interval is a Pollard's-kangaroo
problem (~2^35 group ops): **under a minute on one GPU.**

Bots watch the puzzle addresses in the public mempool 24/7. They extract the
pubkey from any pending spend, crack the key, and broadcast a higher-fee
replacement paying themselves. Puzzle #66 was front-run exactly this way in
September 2024. A normal broadcast loses the prize with near certainty.

**Rule: the sweep transaction must never enter the public mempool. It must
first appear to the world already inside a mined block.**

## Absolute don'ts (any of these loses the race)

- Do NOT import the key into any wallet app (they query servers immediately).
- Do NOT paste the key or address into any website, explorer, or balance checker.
- Do NOT use `sendrawtransaction` against any public node or explorer
  "broadcast" page, and no public "transaction accelerators" (they relay).
- Do NOT post, message, or brag before 6 confirmations. Not even hints.
- Do NOT test-spend a small amount first. One transaction, whole balance, once.

## Procedure

Trigger: hunt71.sh exits and writes `SOLUTION_puzzle71_<ts>.txt` (runner dir
and $HOME on Oracle). Kuma `puzzle71-heartbeat` goes DOWN → Telegram alert.

1. **Copy the solution file off Oracle** to the homelab box over Tailscale ssh.
   Keep a second copy on a USB stick. Do nothing else on Oracle.

2. **Verify offline.** Derive address from the private key with the repo's
   pure-python oracle (no network, no deps):
   ```
   python3 keyhunt_arm_port/tests/gen_ref.py <privhex>
   ```
   Output address must equal `1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU`.
   If keyhunt printed the key in decimal, convert to hex first.

3. **Pick the destination.** A fresh receive address from Jon's hardware /
   cold wallet. Generate it on the wallet device, not on a hot machine.
   (REQUIRED INPUT at solve time — deliberately not pre-written here.)

4. **Build and sign the sweep transaction offline.** One input (the puzzle
   UTXO), one output (destination), generous fee — check the current
   Slipstream minimum at slipstream.mara.com and pay comfortably above it.
   Build/sign with a local library (python `embit` or similar) on a machine
   with networking you control. The signed hex never touches a wallet service.

5. **Submit the raw hex directly to MARA Slipstream** (slipstream.mara.com).
   Slipstream sends the transaction straight to MARA Pool's private mempool;
   it is not relayed publicly and first appears in a mined block.
   - Fallback if Slipstream is dead: contact other large pools' private
     submission channels (Foundry, Luxor, F2Pool) directly. Do not settle for
     a public broadcast unless every private channel is exhausted; a public
     broadcast with a huge fee is a coin-flip at best.

6. **Wait for 6 confirmations.** After the block is buried, the pubkey reveal
   is harmless — the funds already moved. Now it is safe to talk.

7. Afterwards: stop the hunt (`hunt71.sh` already exits on solve), pause the
   two Kuma monitors, and update the project memory.

## Notes

- Odds of ever opening this file in anger: ~1 in 8 million per year at current
  rate. It exists so future-us executes a rehearsed plan instead of
  improvising against sub-minute adversaries.
- Slipstream background: MARA's direct transaction submission service, live
  since Feb 2024 (https://slipstream.mara.com, press: ir.mara.com).
- Kangaroo math: interval [2^70, 2^71), pubkey known → ~2^35.5 expected group
  ops; consumer GPU kangaroo implementations do >1 Gops/s.
