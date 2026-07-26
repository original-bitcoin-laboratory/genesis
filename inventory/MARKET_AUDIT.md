# Commercial subsystem audit (R6)

Static audit of v0.1.0's `market.*` commerce layer and its wiring, from the extracted,
hash-verified tree. Every claim carries a `src:line` anchor. Roadmap R6 asks each path
to be classified **operational / reachable / partial / dormant / absent**.

**Headline finding:** this is **not dead code**. v0.1 shipped a working, three-layer
**decentralized marketplace** — a flood publish/subscribe advert network, a two-party
request/reply purchase protocol wired into the wallet, and a web-of-trust reputation
system seeded by signed reviews. None of it touches the blockchain; it is a separate
broadcast + local-DB layer. A few bootstrapping bits are commented out (below).

---

## 1. Data model (`market.h`)

| Class | Fields | Role |
|---|---|---|
| **`CUser`** (`market.h:25`) | `vAtomsIn` / `vAtomsNew` / `vAtomsOut`, `vLinksOut` | web-of-trust node: "atoms" (reputation tokens) + outbound trust links |
| **`CReview`** (`market.h:72`) | `hashTo`, `mapValue`, `vchPubKeyFrom`, `vchSig`, `nAtoms` | a signed review *of* a product/user; carries reputation weight |
| **`CProduct`** (`market.h:120`) | `addr` (seller `CAddress`), `mapValue`, `mapDetails`, `vOrderForm`, `nSequence`, `vchPubKeyFrom`, `vchSig`, `nAtoms` | a signed, versioned product listing |

Serialization is signature-aware: `GetSigHash()` uses `SER_GETHASH|SER_SKIPSIG`
(`market.h:107,165`) so signatures cover everything *except* themselves; `SER_DISK`
toggles disk-only fields (`nAtoms`), `SER_GETHASH` drops the order form / details from
a product's identity hash (`market.h:151-161`). Globals: `mapProducts`,
`mapMyProducts`, `cs_mapProducts` (`market.h:180-182`).

## 2. Layer 1 — product advertising (flood pub/sub)

Products are distributed by a **generic broadcast/subscription "Advert" channel**
system in `net.*`, *not* by inv/getdata block relay and *not* on-chain.

- Channels are message numbers; `MSG_PRODUCT` / `MSG_TABLE` (`net.h:306`, `net.cpp:202`).
- A seller publishes: UI → `AdvertStartPublish(pnodeLocalHost, MSG_PRODUCT, 0, product)`
  (`ui.cpp:2322`) → `AdvertInsert(obj)` (`net.h:824` → `market.cpp:29`) inserts/updates
  `mapProducts` (newer `nSequence` wins), then floods to subscribers.
- Inventory participation: `MSG_PRODUCT` is a known inv type
  (`main.cpp:1599: case MSG_PRODUCT: return mapProducts.count(inv.hash)`).
- **Ephemerality:** on peer disconnect, `AdvertRemoveSource(this, MSG_PRODUCT, …)`
  drops that node's products (`net.cpp:357`) — *"a node has to stay up to keep its
  broadcast going."* Listings live only while the seller is online.
- `CProduct::CheckProduct()` (`market.cpp:242`) rejects a listing that is **not a
  "summary"** — it must carry no `mapDetails` and no `vOrderForm` (`market.cpp:248`);
  full details arrive later in the order flow. It also looks up the seller's atom
  count via `CReviewDB` (`market.cpp:252-255`).

## 3. Layer 2 — the purchase protocol (request/reply, wallet-integrated)

A complete two-party buy handshake over P2P (`main.cpp` `ProcessMessage`), correlated
by a `hashReply` + `CRequestTracker`:

1. **`checkorder`** (`main.cpp:1974`) — buyer sends a draft order; the seller "has a
   chance to check the order," mints a **fresh key per buyer IP** (`mapReuseKey`,
   reused until spent), and replies `reply(hashReply, 0, scriptPubKey)` where
   `scriptPubKey = <pubkey> OP_CHECKSIG` — the bare-P2PK payment target (`main.cpp:1987-1989`).
2. **`submitorder`** (`main.cpp:1993`) — buyer submits the payment `CWalletTx`; seller
   `AcceptWalletTransaction()` → `AddToWallet()` → `RelayWalletTransaction()` (broadcasts
   the payment), clears the reuse key, replies `reply(hashReply, 0)` confirmation
   (`main.cpp:2000-2011`); failure returns `reply(…, 1)`.
3. **`reply`** (`main.cpp:2015`) — matched against `pfrom->mapRequests` via `CRequestTracker`.

This rides the same **pay-to-IP** transfer mode the GUI exposes (Send Coins → "recipient's
IP address … for online transfer").

## 4. Layer 3 — reputation ("atoms" web of trust)

`CReview::AcceptReview()` (`market.cpp:197`): verify `CKey::Verify` on `GetSigHash`
→ append to the recipient's reviews in `CReviewDB` (`market.cpp:210-212`) → add a
trust link `user.vLinksOut.push_back(hashTo)` (`market.cpp:219`) → **propagate atoms**
via `AddAtomsAndPropagate(hashTo, …)` (`market.cpp:227`).

`AddAtomsAndPropagate` (`market.cpp:143`) is a two-frontier flood over the `vLinksOut`
graph; `CUser::AddAtom` (`market.cpp:109`) implements a **flow-through** rule
(`nFlowthroughRate = 2`, `market.h:9`): incoming atoms accumulate in `vAtomsNew`, and
once ≥2 (or none out yet) a **randomly chosen** one flows to `vAtomsOut` to propagate
onward; the zero atom never propagates; origin atoms always do (`market.cpp:120-140`).

## 5. Classification

| # | Path | Class | Anchor | Note |
|---|---|---|---|---|
| 1 | Product publish/subscribe (Advert flood) | **operational** | `ui.cpp:2322`, `net.h:819-824`, `market.cpp:29` | ephemeral; off-chain |
| 2 | Product validation + seller atom lookup | **operational** | `market.cpp:237-264` | "summary only" constraint |
| 3 | `checkorder` → payment-key reply | **operational** | `main.cpp:1974-1989` | fresh key per buyer IP |
| 4 | `submitorder` → accept/relay/confirm | **operational** | `main.cpp:1993-2011` | wallet-integrated |
| 5 | `reply` / `CRequestTracker` correlation | **operational** | `main.cpp:2015`+ | request/response |
| 6 | `review` accept + relay (P2P) | **operational** | `main.cpp:1921-1935` | signature-checked |
| 7 | Review submission (UI) | **operational** | `ui.cpp:2787` | |
| 8 | Review storage (`CReviewDB`) | **operational** | `db.h:280`, `db.cpp:474-480` | `ReadReviews/WriteReviews` |
| 9 | Atom propagation through review links | **partial** | `market.cpp:143-190,225-228` | works, but seeded only by reviews |
| 10 | **Origin-atom seeding** | **dormant** | `main.cpp:1226-1230` (commented) | new origin atoms never injected here |
| 11 | Product add/update/delete notifications | **dormant** | `market.cpp:50-53,63` (commented) | UI callbacks stubbed |
| 12 | `mapMyProducts` persistence | **partial/absent** | `market.cpp:20-21` (`"later figure out how these are persisted"`) | own listings are memory-only |

Nothing in the subsystem is fully **absent** — every piece is present in source; the
gaps are commented bootstrapping (10, 11) and an unfinished persistence TODO (12).

## 6. Findings

- **A working decentralized marketplace shipped in v0.1** — signed listings, a
  request/reply purchase protocol tied to the wallet, and a reputation graph — years
  before "Bitcoin is just money" became the dominant framing. This corroborates the
  lab thesis that v0.1 is a *general financial predicate engine*, not only a currency.
- **Off-chain by design.** Products/reviews/atoms live in a **broadcast + local DB**
  layer (`CReviewDB`, `mapProducts`), never on the blockchain. Listings are **ephemeral**
  (die with the seller's connection). This is a flood pub/sub network with hop counts
  and subscriptions (`MSG_TABLE`/`MSG_PRODUCT`), distinct from block/tx relay.
- **Privacy touch:** a fresh receiving key per buyer IP (`mapReuseKey`, `main.cpp:1983`).
- **Reputation is a flow-through web of trust** (random-atom propagation, rate 2),
  bootstrapped by signed reviews — but the *origin* atom seeding is commented out
  (`main.cpp:1230`), so the graph propagates trust it is never formally given a root
  for through that path.

## 7. Boundary & next

This is a **static audit** (Tier-4 interpretation over Tier-0 source). The natural
executable follow-on — mirroring the lab's `tx_sighash` work — is a MODEL of the
**review/product `GetSigHash` (`SER_SKIPSIG`) + `CKey::Verify`** signature and the
`AddAtom` flow-through, so the commerce signatures and reputation math can be *run*,
not just read. Filed as a deepening, not a gap.
