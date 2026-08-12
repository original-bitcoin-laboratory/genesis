# Bitcoin's script resource limits were retrofitted in mid-2010

**12 August 2026.** Bitcoin Script enforces several resource limits. Four of them cap the size of a
pushed stack element, the total script size, the stack depth, and the size of a numeric operand.
They are commonly treated as part of the original design.

**None of the four is in the January 2009 release.** All four were added on **29 July 2010**, in a
single commit whose message describes a makefile change, and the element and numeric caps were
tightened seventeen days later by a commit whose message is *"misc changes"*. *(A fifth limit — the
op-count cap — arrives separately at v0.3.7 and is noted but not dated here.)*

This note dates the four, gives the method to reproduce the dating, and states one consequence.

> ### What is already known, and what this note adds
>
> **The tightening commit is documented in a BIP.** [BIP-347](https://github.com/bitcoin/bips/blob/master/bip-0347.mediawiki)
> (OP_CAT reactivation) cites `4bd188c` — *"In 2010, a single commit disabled OP_CAT, along with
> another 15 opcodes"* — and records that the element cap stood at 5,000 bytes at that moment:
> *"As Bitcoin at that time had a maximum stack element size of 5000 bytes, the effect of this
> expansion was limited to 5000 bytes."*
>
> **BIP-347 does not say when that 5,000-byte cap was introduced.** It establishes that the limit
> *existed*; it makes no claim about when it arrived, or about the other three caps.
>
> ```
> ALREADY DOCUMENTED    4bd188c disabling OP_CAT and 15 opcodes         (BIP-347)
>                       that a 5,000-byte element cap existed in 2010   (BIP-347)
>
> ADDED HERE            the DATE OF INTRODUCTION -- 757f076, 29 Jul 2010
>                       that four caps arrive together in one commit
>                       that the commit message describes only a makefile change
>                       the byte-identity provenance result below
> ```
>
> **No priority is claimed even for the added part.** A literature search was performed and is
> reported here; it was not exhaustive, and the commits are public to anyone who looks.

---

## The finding

```
Jan 2009      v0.1.0                     NO LIMITS OF ANY KIND
30 Aug 2009   e071a3f6 "First commit"    NO LIMITS      35,279 B
03 Feb 2010   53d5080                    NO LIMITS      35,611 B
12 Feb 2010   98500d7                    NO LIMITS      35,606 B
14-28 Jul 2010  every commit tested      NO LIMITS      34,472 / 35,606 B
29 Jul 2010   17b2740                    NO LIMITS      35,606 B   <- last uncapped state
29 Jul 2010   757f076                    ALL FOUR       39,255 B   <- +3,649 bytes
15 Aug 2010   4bd188c                    TIGHTENED
```

### The commit that installed them

```
757f0769d8360ea043f469f3a35f6ec204740446
2010-07-29T20:27:12Z    author field: s_nakamoto
message: "reverted makefile.unix wx-config -- version 0.3.6"

  script.cpp     +671  -643      (102 of the added lines are blank or brace-only)
  script.h       +26   -1
  bignum.h       +2    -1
  makefile.unix  +14   -5        the only file the message refers to
  serialize.h    +2    -2
  setup.nsi      +3    -3
```

The additions to `script.cpp` that impose limits:

```diff
+static const size_t nMaxNumSize = 258;                     numeric operand cap
+    if (script.size() > 20000)                             script size cap
+            if (vchPushValue.size() > 5000)                pushed element cap
+                    if (stacktop(-1).size() > 5000)
+            if (stack.size() + altstack.size() > 1000)     stack depth cap
```

**Four limits, not five.** The **op-count** limit (`nOpCount > 200`) is **not** in this commit; it
arrives at v0.3.7. And the script-size cap here is **20,000**, later tightened to 10,000. So the
regime assembles across three releases, with this commit carrying the bulk of it.

### The commit that tightened them

```
4bd188c4383d6e614e18f79dc337fbabe8464c82
2010-08-15T21:05:16Z    author: s_nakamoto    SVN r131    shipped in v0.3.10 (08fee752)
message: "misc changes"
```

```diff
-            if (vchPushValue.size() > 5000)
+            if (vchPushValue.size() > 520)
-                    if (stacktop(-1).size() > 5000)
+                    if (stacktop(-1).size() > 520)
```

The same commit cuts the numeric cap `258 → 4` and adds a pre-switch guard disabling `OP_CAT`,
`OP_SUBSTR`, `OP_MUL` and siblings — the opcode disabling that BIP-347 exists to reverse.

> **⚠️ A citation discrepancy, offered as an observation rather than a correction.** BIP-347's
> reference for this commit reads *"S. Nakamoto, 'misc changes', **Aug 25 2010**"*. **The commit's
> own metadata gives 2010-08-15T21:05:16Z in both the author and committer fields**, and its
> `git-svn-id` trailer is `trunk@131`.
>
> The ten-day gap is not explained by the commit record: the v0.3.10 build commit `08fee752` is also
> dated 15 August (22:46:58Z, ninety minutes later), and the commits actually dated 25 August 2010
> are the alert-system and safe-mode changes. **It may correspond to a release or announcement date
> rather than the commit; the reference attributes it to the commit.** Nothing in BIP-347's argument
> depends on the date, and nothing here contests its substance.

> **⇒ Bitcoin Script's resource-limit regime arrived in mid-2010, across three releases, with the
> bulk of it in one commit whose message describes a makefile change and the tightening in another
> whose message is "misc changes".**

**The full assembly, so no step is overstated:**

```
v0.3.6   29 Jul 2010   757f076   element 5000 · script 20000 · stack 1000 · numeric 258
                                   ^ dated here, by fetched file
v0.3.7        2010        --      op-count 200 · script 20000 -> 10000
                                   ^ NOT dated here. Stated from secondary reading; the
                                     commit was not fetched and this row is not evidence
v0.3.10  15 Aug 2010   4bd188c   element 5000 -> 520 · numeric 258 -> 4 · opcodes disabled
                                   ^ dated here, by fetched commit
```

---

## Method

**No inference. Every row above is a fetched file.**

Each commit in `bitcoin/bitcoin` between 30 August 2009 and 15 August 2010 was retrieved at
`raw.githubusercontent.com/bitcoin/bitcoin/<sha>/script.cpp` and tested for the literal cap
expressions. The transition is exact and same-day: `17b2740` carries none of them at 35,606 bytes;
`757f076` carries all of them at 39,255 bytes.

```bash
# reproduce the transition in two fetches
for sha in 17b274028 757f0769d; do
  curl -s "https://raw.githubusercontent.com/bitcoin/bitcoin/$sha/script.cpp" \
    | grep -c 'vchPushValue.size() > 5000'
done      # -> 0  then  1

# and read the installing commit directly
gh api repos/bitcoin/bitcoin/commits/757f0769d --jq '.files[] | "\(.filename) +\(.additions) -\(.deletions)"'
```

**Genesis-side confirmation** was executed rather than read. The January 2009 interpreter was
compiled from the authentic `script.cpp` and evaluated against the script `<N bytes> OP_DROP OP_1`
at ten sizes from 71 to 17,088 bytes. **It accepts every one.** Its only `.size()` tests are
*minimum* stack-depth guards, and push handling is `opcode <= OP_PUSHDATA4` — a four-byte length
prefix.

---

## A provenance result, obtained incidentally

While fetching `script.cpp` at the first commit of `bitcoin/bitcoin` in order to date the caps, it
was compared against the copy preserved in the Satoshi Nakamoto Institute's v0.1.0 archive:

```
bitcoin/bitcoin @ e071a3f6, 30 Aug 2009    35,279 B   sha256 347c7526932d42a4d10ae487150b709e…
SNI v0.1.0 archive, script.cpp             35,279 B   sha256 347c7526932d42a4d10ae487150b709e…
                                           BYTE-IDENTICAL
```

**Two things follow.** `script.cpp` was unchanged for seven months, from the January 2009 release to
the first commit of the canonical repository. And the archive copy is **independently authenticated
against `bitcoin/bitcoin` itself** — for this file, provenance no longer rests on custody and
published digests alone.

---

## One consequence, stated as a corollary rather than a motivation

The NIST post-quantum signature standards — **ML-DSA (FIPS 204)** and **SLH-DSA (FIPS 205)**,
finalised August 2024 — produce signatures far larger than secp256k1's ~71 bytes. Sizes below are
the standards' own, measured from OpenSSL 3.5.4 output. Against the dated limits:

```
                          before 29 Jul 2010    29 Jul – 15 Aug 2010    after 15 Aug 2010
                          (no limit)            (5,000 B element cap)   (520 B element cap)
ML-DSA-44      2,420 B    fits                  fits                    no
ML-DSA-65      3,309 B    fits                  fits                    no
ML-DSA-87      4,627 B    fits                  fits                    no
SLH-DSA-128s   7,856 B    fits                  no                      no
SLH-DSA-192s  16,224 B    fits                  no                      no
SLH-DSA-128f  17,088 B    fits                  no                      no
```

**This is an observation about byte sizes against a byte limit, and nothing more.** It does not
claim the 2010 commits considered post-quantum cryptography — they plainly did not; both are
denial-of-service hardening, seventeen years before the standards existed. It does not claim any
post-quantum scheme would have been *usable* in 2009: fitting on the stack is necessary, not
sufficient, and says nothing about verification opcodes, transaction size, block capacity or fees.

> **What it does establish is narrow and checkable: the constraint that today rules out every
> standardised post-quantum signature at the script layer is not a property of Bitcoin's original
> design. It was introduced later, for unrelated reasons.**

---

## Limits of this note

```
NOT a novelty claim      no literature search was performed; the commits are public
NOT a claim about intent the commit messages are quoted, not interpreted. Why script.cpp was
                         rewritten in a commit about makefile.unix is not established here
NOT a completeness claim only script.cpp was tracked. Other consensus limits (block size,
                         sigops, transaction size) are not covered
NOT a recommendation     nothing here argues for or against changing any limit
BOUNDED window           30 Aug 2009 to 15 Aug 2010. The repository's history begins at the
                         first commit; the Jan-Aug 2009 interval is covered by the archive
                         copy, which is byte-identical to that first commit
```

---

## Artifacts

The experiment source, its captured output, the fetched upstream `script.cpp`, and the full
per-commit dating record are published with a SHA-256 manifest. The reproduction is two `curl`
calls; the compiled check requires g++ and the interpreter source.

**Corrections to this note will be published, dated, and never made silently.**
