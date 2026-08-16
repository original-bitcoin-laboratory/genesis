# obl-metric — replication package

**The artifacts behind *Reference-Relative Protocol-Profile Comparison*.** Every numerical result
and table in that paper re-derives from these files, and the paper names each of them by full
SHA-256 so a reader can tell whether the copy they hold is the copy it reports on.

## Verify before you trust

```bash
sha256sum obl_metric.py audit_descendants.py audit_btc.py audit_btg.py \
          figures/mismatch_heatmap.py figures/mismatch_heatmap_v010.png \
          tables/audit_descendants.json tables/audit_btc.json \
          artifacts/comparison.json artifacts/axis_matrix.csv artifacts/comparison.csv
```

```
obl_metric.py                      c57741458a459169e909aefdf5c1516e0460458c48d7c80d311770edd93752c2
audit_descendants.py               74daf47d77aa8266561963f8e4115eaa7376859450c1c9b923b8f94f40240214
audit_btc.py                       daa7dcaebc464a206881be1107b463b510a61a86906d747012e7bc2013e01369
audit_btg.py                       8de0a38b4e968662f2ea0e2d604a1c77a55ca2874bc54e5a381b2165679a5f65
figures/mismatch_heatmap.py        2406483e3d637311002257d4f49f915785de81715b417d387a4780b91477feab
figures/mismatch_heatmap_v010.png  67549237b042d335f7149b6677900fa7ad7bee5c1ffef4f634cbb034ec1281ff
tables/audit_descendants.json      a35b7def457c9bda17d8c05edec334fb2aec827858cd6706c42569727c184ebc
tables/audit_btc.json              ab63eef2f14674fcce02149a8d4d9136164706e551722bd535b2428d786f1efb
artifacts/comparison.json          2209d84e4cf03c7297016fec4cda05d23b00331ce3bc42601c5729801528bcc9
artifacts/axis_matrix.csv          191d70b5ee1206ec42e9184fbb5ce2624c99bd94788087b1f87a5c1f0175aaf2
artifacts/comparison.csv           71bb2fa5a06cf72a68ef6fa80578fc1eab3ed0d04da432518c675b46eb254e18
```

The eight generated tables are covered by one manifest digest, computed as SHA-256 over each
file's name followed by the SHA-256 of its bytes, in sorted filename order:

```
tables/table*.md   8 files
11afe004a45e10c0fd655aff7767d47a41e6f02e1158fba3c55028a751a8f221
```

## Reproduce

```bash
python obl_metric.py        # regenerates artifacts/ and tables/ -- deterministic, no wall clock
python stress_test.py       # the adversarial suite the paper was hardened against
python build_paper.py       # rebuilds paper.md from paper.template.md
```

⚠️ **Line endings are load-bearing here.** `artifacts/comparison.json` is LF; the two CSVs are CRLF
throughout, because `csv.writer` emits CRLF on every platform per RFC 4180. The repository's
`.gitattributes` disables translation so a clone reproduces these bytes rather than the local
platform's idea of them. If a digest disagrees, check that first.

## What each file is

```
obl_metric.py            the scoring engine; carries the axis dataset and emits everything below
audit_btc.py             fetches the BIPs repository and confirms the BIP-backed BTC cells
audit_descendants.py     fetches the BSV / BCH / ABC specifications and BTG's chainparams.cpp
audit_btg.py             tests chain-selection criterion (2) -- was Bitcoin Gold producing blocks
                         at the freeze. It verifies no cell and emits no citation ledger
figures/                 the heatmap renderer and the figure it produces
tables/audit_*.json      the audit LEDGERS: per probe, the URL, HTTP status, control outcome and
                         the SHA-256 of the retrieved body, with the run timestamp
tables/table*.md         the generated tables the manuscript substitutes
artifacts/               the engine's serialised outputs -- full cell record, axis matrix, rates
```

## Licence

MIT for the code, as for the rest of this repository. The manuscript is CC BY 4.0.

**NOT money.** The experimental chains and artifacts associated with this work carry no monetary
value: no premine, no sale, no token, no price.
