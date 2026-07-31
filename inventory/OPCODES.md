# OBL-JAN09 — Opcode & SIGHASH inventory

> **Generated** by `scripts/inventory-symbols.py` from the extracted v0.1.0 source.
> Declaration is from the `opcodetype` enum in `script.h`; **EvalScript case** means an
> execution branch of that opcode is present in `script.cpp`'s `EvalScript` — i.e. it is
> *implemented* (rung 2 of the evidence ladder), not merely declared (rung 1). Reachability
> and consensus-execution are established later (R3–R4).

## Source provenance

| File | lines | sha256 |
|---|--:|---|
| `script.h` | 597 | `f905858b5d6d4593a3051b593c45fb5a8dd4cd38b5636c5e4456060b034fa218` |
| `script.cpp` | 1128 | `347c7526932d42a4d10ae487150b709e2ead737aa4b05f50aa9e2eefeb05a5b5` |

## Signature-hash modes (`script.h`)

| Mode | value |
|---|--:|
| `SIGHASH_ALL` | 0x01 (1) |
| `SIGHASH_NONE` | 0x02 (2) |
| `SIGHASH_SINGLE` | 0x03 (3) |
| `SIGHASH_ANYONECANPAY` | 0x80 (128) |

## Opcodes (106 distinct values, 2 aliases)

**94** opcodes have an `EvalScript` execution branch.
 Explicitly disabled / commented-out in `script.cpp`: `OP_NOTEQUAL` (`script.cpp:486`).

Each opcode carries a `file:line` source witness: `script.h` for its `opcodetype`
declaration and `script.cpp` for its `EvalScript` execution branch (both hashed above).

| Opcode | hex | dec | category | decl (`script.h`) | EvalScript (`script.cpp`) | note |
|---|---|--:|---|--:|--:|---|
| `OP_0` | 0x00 | 0 | push value | L20 | — |  |
| `OP_FALSE` | 0x00 | 0 | push value | L21 |  | alias of `OP_0` |
| `OP_PUSHDATA1` | 0x4c | 76 | push value | L22 | — |  |
| `OP_PUSHDATA2` | 0x4d | 77 | push value | L23 | — |  |
| `OP_PUSHDATA4` | 0x4e | 78 | push value | L24 | — |  |
| `OP_1NEGATE` | 0x4f | 79 | push value | L25 | L78 |  |
| `OP_RESERVED` | 0x50 | 80 | push value | L26 | — |  |
| `OP_1` | 0x51 | 81 | push value | L27 | L79 |  |
| `OP_TRUE` | 0x51 | 81 | push value | L28 |  | alias of `OP_1` |
| `OP_2` | 0x52 | 82 | push value | L29 | L80 |  |
| `OP_3` | 0x53 | 83 | push value | L30 | L81 |  |
| `OP_4` | 0x54 | 84 | push value | L31 | L82 |  |
| `OP_5` | 0x55 | 85 | push value | L32 | L83 |  |
| `OP_6` | 0x56 | 86 | push value | L33 | L84 |  |
| `OP_7` | 0x57 | 87 | push value | L34 | L85 |  |
| `OP_8` | 0x58 | 88 | push value | L35 | L86 |  |
| `OP_9` | 0x59 | 89 | push value | L36 | L87 |  |
| `OP_10` | 0x5a | 90 | push value | L37 | L88 |  |
| `OP_11` | 0x5b | 91 | push value | L38 | L89 |  |
| `OP_12` | 0x5c | 92 | push value | L39 | L90 |  |
| `OP_13` | 0x5d | 93 | push value | L40 | L91 |  |
| `OP_14` | 0x5e | 94 | push value | L41 | L92 |  |
| `OP_15` | 0x5f | 95 | push value | L42 | L93 |  |
| `OP_16` | 0x60 | 96 | push value | L43 | L94 |  |
| `OP_NOP` | 0x61 | 97 | control | L46 | L106 |  |
| `OP_VER` | 0x62 | 98 | control | L47 | L109 |  |
| `OP_IF` | 0x63 | 99 | control | L48 | L116 |  |
| `OP_NOTIF` | 0x64 | 100 | control | L49 | L117 |  |
| `OP_VERIF` | 0x65 | 101 | control | L50 | L118 |  |
| `OP_VERNOTIF` | 0x66 | 102 | control | L51 | L119 |  |
| `OP_ELSE` | 0x67 | 103 | control | L52 | L140 |  |
| `OP_ENDIF` | 0x68 | 104 | control | L53 | L148 |  |
| `OP_VERIFY` | 0x69 | 105 | control | L54 | L156 |  |
| `OP_RETURN` | 0x6a | 106 | control | L55 | L170 |  |
| `OP_TOALTSTACK` | 0x6b | 107 | stack ops | L58 | L180 |  |
| `OP_FROMALTSTACK` | 0x6c | 108 | stack ops | L59 | L189 |  |
| `OP_2DROP` | 0x6d | 109 | stack ops | L60 | L198 |  |
| `OP_2DUP` | 0x6e | 110 | stack ops | L61 | L206 |  |
| `OP_3DUP` | 0x6f | 111 | stack ops | L62 | L218 |  |
| `OP_2OVER` | 0x70 | 112 | stack ops | L63 | L232 |  |
| `OP_2ROT` | 0x71 | 113 | stack ops | L64 | L244 |  |
| `OP_2SWAP` | 0x72 | 114 | stack ops | L65 | L257 |  |
| `OP_IFDUP` | 0x73 | 115 | stack ops | L66 | L267 |  |
| `OP_DEPTH` | 0x74 | 116 | stack ops | L67 | L278 |  |
| `OP_DROP` | 0x75 | 117 | stack ops | L68 | L286 |  |
| `OP_DUP` | 0x76 | 118 | stack ops | L69 | L295 |  |
| `OP_NIP` | 0x77 | 119 | stack ops | L70 | L305 |  |
| `OP_OVER` | 0x78 | 120 | stack ops | L71 | L314 |  |
| `OP_PICK` | 0x79 | 121 | stack ops | L72 | L324 |  |
| `OP_ROLL` | 0x7a | 122 | stack ops | L73 | L325 |  |
| `OP_ROT` | 0x7b | 123 | stack ops | L74 | L342 |  |
| `OP_SWAP` | 0x7c | 124 | stack ops | L75 | L354 |  |
| `OP_TUCK` | 0x7d | 125 | stack ops | L76 | L363 |  |
| `OP_CAT` | 0x7e | 126 | splice ops | L79 | L377 |  |
| `OP_SUBSTR` | 0x7f | 127 | splice ops | L80 | L389 |  |
| `OP_LEFT` | 0x80 | 128 | splice ops | L81 | L410 |  |
| `OP_RIGHT` | 0x81 | 129 | splice ops | L82 | L411 |  |
| `OP_SIZE` | 0x82 | 130 | splice ops | L83 | L430 |  |
| `OP_INVERT` | 0x83 | 131 | bit logic | L86 | L444 |  |
| `OP_AND` | 0x84 | 132 | bit logic | L87 | L455 |  |
| `OP_OR` | 0x85 | 133 | bit logic | L88 | L456 |  |
| `OP_XOR` | 0x86 | 134 | bit logic | L89 | L457 |  |
| `OP_EQUAL` | 0x87 | 135 | bit logic | L90 | L484 |  |
| `OP_EQUALVERIFY` | 0x88 | 136 | bit logic | L91 | L485 |  |
| `OP_RESERVED1` | 0x89 | 137 | bit logic | L92 | — |  |
| `OP_RESERVED2` | 0x8a | 138 | bit logic | L93 | — |  |
| `OP_1ADD` | 0x8b | 139 | numeric | L96 | L516 |  |
| `OP_1SUB` | 0x8c | 140 | numeric | L97 | L517 |  |
| `OP_2MUL` | 0x8d | 141 | numeric | L98 | L518 |  |
| `OP_2DIV` | 0x8e | 142 | numeric | L99 | L519 |  |
| `OP_NEGATE` | 0x8f | 143 | numeric | L100 | L520 |  |
| `OP_ABS` | 0x90 | 144 | numeric | L101 | L521 |  |
| `OP_NOT` | 0x91 | 145 | numeric | L102 | L522 |  |
| `OP_0NOTEQUAL` | 0x92 | 146 | numeric | L103 | L523 |  |
| `OP_ADD` | 0x93 | 147 | numeric | L105 | L545 |  |
| `OP_SUB` | 0x94 | 148 | numeric | L106 | L546 |  |
| `OP_MUL` | 0x95 | 149 | numeric | L107 | L547 |  |
| `OP_DIV` | 0x96 | 150 | numeric | L108 | L548 |  |
| `OP_MOD` | 0x97 | 151 | numeric | L109 | L549 |  |
| `OP_LSHIFT` | 0x98 | 152 | numeric | L110 | L550 |  |
| `OP_RSHIFT` | 0x99 | 153 | numeric | L111 | L551 |  |
| `OP_BOOLAND` | 0x9a | 154 | numeric | L113 | L552 |  |
| `OP_BOOLOR` | 0x9b | 155 | numeric | L114 | L553 |  |
| `OP_NUMEQUAL` | 0x9c | 156 | numeric | L115 | L554 |  |
| `OP_NUMEQUALVERIFY` | 0x9d | 157 | numeric | L116 | L555 |  |
| `OP_NUMNOTEQUAL` | 0x9e | 158 | numeric | L117 | L556 |  |
| `OP_LESSTHAN` | 0x9f | 159 | numeric | L118 | L557 |  |
| `OP_GREATERTHAN` | 0xa0 | 160 | numeric | L119 | L558 |  |
| `OP_LESSTHANOREQUAL` | 0xa1 | 161 | numeric | L120 | L559 |  |
| `OP_GREATERTHANOREQUAL` | 0xa2 | 162 | numeric | L121 | L560 |  |
| `OP_MIN` | 0xa3 | 163 | numeric | L122 | L561 |  |
| `OP_MAX` | 0xa4 | 164 | numeric | L123 | L562 |  |
| `OP_WITHIN` | 0xa5 | 165 | numeric | L125 | L633 |  |
| `OP_RIPEMD160` | 0xa6 | 166 | crypto | L128 | L653 |  |
| `OP_SHA1` | 0xa7 | 167 | crypto | L129 | L654 |  |
| `OP_SHA256` | 0xa8 | 168 | crypto | L130 | L655 |  |
| `OP_HASH160` | 0xa9 | 169 | crypto | L131 | L656 |  |
| `OP_HASH256` | 0xaa | 170 | crypto | L132 | L657 |  |
| `OP_CODESEPARATOR` | 0xab | 171 | crypto | L133 | L685 |  |
| `OP_CHECKSIG` | 0xac | 172 | crypto | L134 | L692 |  |
| `OP_CHECKSIGVERIFY` | 0xad | 173 | crypto | L135 | L693 |  |
| `OP_CHECKMULTISIG` | 0xae | 174 | crypto | L136 | L727 |  |
| `OP_CHECKMULTISIGVERIFY` | 0xaf | 175 | crypto | L137 | L728 |  |
| `OP_SINGLEBYTE_END` | 0xf0 | 240 | multi-byte opcodes | L141 | — |  |
| `OP_DOUBLEBYTE_BEGIN` | 0xf000 | 61440 | multi-byte opcodes | L142 | — |  |
| `OP_PUBKEY` | 0xf001 | 61441 | template matching params | L145 | — |  |
| `OP_PUBKEYHASH` | 0xf002 | 61442 | template matching params | L146 | — |  |
| `OP_INVALIDOPCODE` | 0xffff | 65535 | template matching params | L150 | — |  |

