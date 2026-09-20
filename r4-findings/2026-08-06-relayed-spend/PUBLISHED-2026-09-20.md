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
