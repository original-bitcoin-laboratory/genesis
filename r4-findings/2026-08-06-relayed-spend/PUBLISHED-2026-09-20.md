# Binding records published beside the sealed set — 20 September 2026

The set's `EVIDENCE_MANIFEST.json`, sealed by `SHA256SUMS` on 9 August 2026, pins 104 files of the run's evidence
directory by digest; among them the four process-image binding records and the script that captured them:

```
capture_binding.ps1                              09de2144…
nodeA/EXECUTED_BINARY_BINDING_nodeA_pre.json     9b9ce4c5…
nodeA/EXECUTED_BINARY_BINDING_nodeA_post.json    287b0d8d…
nodeB/EXECUTED_BINARY_BINDING_nodeB_pre.json     26be5490…
nodeB/EXECUTED_BINARY_BINDING_nodeB_post.json    d4d481e2…
```

Until 20 September 2026 the records themselves were not in this repository: the evidence directory is kept out of it
(`.gitignore`), and `FINDINGS.md` summarised them. An adversarial review observed that the one run graded
`JAN09-EXECUTED` was the one whose binding records a reader could not open. The five files are now published here,
under the paths the manifest names; their digests are the manifest's, so the seal is unchanged and nothing in the
set is edited. Each record binds a running process (PID, start time, image path) to `bitcoin.exe` sha256
`fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d`, the archive's binary, and to its two DLLs,
before and after the run. The guest hostname and the guest user's data directory are the VM's.

The digest `fbcac071…` is the laboratory's own reading of the `bitcoin.exe` inside the archive served as
`bitcoin-0.1.0.rar` (sha256 `8b17eb9a…`); no 2009-era publication of that binary's hash is known
(`provenance/SOURCEFORGE_PUBLISHED_HASHES.md`). The binding therefore proves that one uninterrupted process ran that
file. That the file is the January 2009 build rests on the archive's custody and its internal evidence
(`common/VERSION_LABEL.md`), as every `JAN09-` grade does.
