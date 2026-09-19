# Adversarial review — partial receipt, 20 September 2026

*Recorded as received. The session was an AI session commissioned by the operator, working from
the adversarial-review brief in `../../REPRODUCTIONS.md`, with no access to this laboratory's
workspace. Its runtime could not reach GitHub, so it audited the test sources rather than executing
them, and says so. The transcript was cut after the second row of its table; what follows is all
that was received. Nothing here has been edited by the laboratory; both findings were corrected the
same day (`OBL-F-0005`; `docs/NOV08_GENESIS.md`).*

---

**Scope and execution limitation.** I audited the public register rows and the cited public artifacts, checked the cited Bitcoin commits against the public `bitcoin/bitcoin` records available to me, and inspected the derivative test logic. I could not honestly claim to have *executed* the laboratory's repository tests in this runtime: the execution environment could not establish a network connection to `github.com`. Accordingly, the derivative section below is a source-level audit of the tests and their assertions, not a fabricated report of successful runs.

| file · line | the claim | the defect | severity | what would fix it |
| --- | --- | --- | --- | --- |
| `genesis/FINDINGS-REGISTER.md:199` | F-0005 says the Nov-2008 genesis coinbase has "no external anchor to a date." | The cited artifact itself now says there is an external anchor: a **17 November 2008 email**. It carefully says that email does **not authenticate the bytes**, which is a narrower and defensible statement. The register's categorical "no external anchor to a date" is therefore contradicted by its own artifact. | **wrong** | Make the claim distinguish "dates the transmission/description" from "authenticates the exact bytes," and cite the latter limitation. |
| `genesis/docs/NOV08_GENESIS.md:195` | The genesis artifact characterises the file as a "developer's test fixture, not a commitment." | That is a statement about the developer's purpose or intent. The artifact does not establish that motive merely from the bytes and provenance chain; indeed the same document concedes that its evidence does not authenticate the bytes to a date. | **unsupported as written / style** | (the transcript was cut here) |

*(received text ends)*
