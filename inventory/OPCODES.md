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
 Explicitly disabled / commented-out in `script.cpp`: `OP_NOTEQUAL`.

| Opcode | hex | dec | category | EvalScript case | note |
|---|---|--:|---|:--:|---|
| `OP_0` | 0x00 | 0 | push value | — |  |
| `OP_FALSE` | 0x00 | 0 | push value |  | alias of `OP_0` |
| `OP_PUSHDATA1` | 0x4c | 76 | push value | — |  |
| `OP_PUSHDATA2` | 0x4d | 77 | push value | — |  |
| `OP_PUSHDATA4` | 0x4e | 78 | push value | — |  |
| `OP_1NEGATE` | 0x4f | 79 | push value | yes |  |
| `OP_RESERVED` | 0x50 | 80 | push value | — |  |
| `OP_1` | 0x51 | 81 | push value | yes |  |
| `OP_TRUE` | 0x51 | 81 | push value |  | alias of `OP_1` |
| `OP_2` | 0x52 | 82 | push value | yes |  |
| `OP_3` | 0x53 | 83 | push value | yes |  |
| `OP_4` | 0x54 | 84 | push value | yes |  |
| `OP_5` | 0x55 | 85 | push value | yes |  |
| `OP_6` | 0x56 | 86 | push value | yes |  |
| `OP_7` | 0x57 | 87 | push value | yes |  |
| `OP_8` | 0x58 | 88 | push value | yes |  |
| `OP_9` | 0x59 | 89 | push value | yes |  |
| `OP_10` | 0x5a | 90 | push value | yes |  |
| `OP_11` | 0x5b | 91 | push value | yes |  |
| `OP_12` | 0x5c | 92 | push value | yes |  |
| `OP_13` | 0x5d | 93 | push value | yes |  |
| `OP_14` | 0x5e | 94 | push value | yes |  |
| `OP_15` | 0x5f | 95 | push value | yes |  |
| `OP_16` | 0x60 | 96 | push value | yes |  |
| `OP_NOP` | 0x61 | 97 | control | yes |  |
| `OP_VER` | 0x62 | 98 | control | yes |  |
| `OP_IF` | 0x63 | 99 | control | yes |  |
| `OP_NOTIF` | 0x64 | 100 | control | yes |  |
| `OP_VERIF` | 0x65 | 101 | control | yes |  |
| `OP_VERNOTIF` | 0x66 | 102 | control | yes |  |
| `OP_ELSE` | 0x67 | 103 | control | yes |  |
| `OP_ENDIF` | 0x68 | 104 | control | yes |  |
| `OP_VERIFY` | 0x69 | 105 | control | yes |  |
| `OP_RETURN` | 0x6a | 106 | control | yes |  |
| `OP_TOALTSTACK` | 0x6b | 107 | stack ops | yes |  |
| `OP_FROMALTSTACK` | 0x6c | 108 | stack ops | yes |  |
| `OP_2DROP` | 0x6d | 109 | stack ops | yes |  |
| `OP_2DUP` | 0x6e | 110 | stack ops | yes |  |
| `OP_3DUP` | 0x6f | 111 | stack ops | yes |  |
| `OP_2OVER` | 0x70 | 112 | stack ops | yes |  |
| `OP_2ROT` | 0x71 | 113 | stack ops | yes |  |
| `OP_2SWAP` | 0x72 | 114 | stack ops | yes |  |
| `OP_IFDUP` | 0x73 | 115 | stack ops | yes |  |
| `OP_DEPTH` | 0x74 | 116 | stack ops | yes |  |
| `OP_DROP` | 0x75 | 117 | stack ops | yes |  |
| `OP_DUP` | 0x76 | 118 | stack ops | yes |  |
| `OP_NIP` | 0x77 | 119 | stack ops | yes |  |
| `OP_OVER` | 0x78 | 120 | stack ops | yes |  |
| `OP_PICK` | 0x79 | 121 | stack ops | yes |  |
| `OP_ROLL` | 0x7a | 122 | stack ops | yes |  |
| `OP_ROT` | 0x7b | 123 | stack ops | yes |  |
| `OP_SWAP` | 0x7c | 124 | stack ops | yes |  |
| `OP_TUCK` | 0x7d | 125 | stack ops | yes |  |
| `OP_CAT` | 0x7e | 126 | splice ops | yes |  |
| `OP_SUBSTR` | 0x7f | 127 | splice ops | yes |  |
| `OP_LEFT` | 0x80 | 128 | splice ops | yes |  |
| `OP_RIGHT` | 0x81 | 129 | splice ops | yes |  |
| `OP_SIZE` | 0x82 | 130 | splice ops | yes |  |
| `OP_INVERT` | 0x83 | 131 | bit logic | yes |  |
| `OP_AND` | 0x84 | 132 | bit logic | yes |  |
| `OP_OR` | 0x85 | 133 | bit logic | yes |  |
| `OP_XOR` | 0x86 | 134 | bit logic | yes |  |
| `OP_EQUAL` | 0x87 | 135 | bit logic | yes |  |
| `OP_EQUALVERIFY` | 0x88 | 136 | bit logic | yes |  |
| `OP_RESERVED1` | 0x89 | 137 | bit logic | — |  |
| `OP_RESERVED2` | 0x8a | 138 | bit logic | — |  |
| `OP_1ADD` | 0x8b | 139 | numeric | yes |  |
| `OP_1SUB` | 0x8c | 140 | numeric | yes |  |
| `OP_2MUL` | 0x8d | 141 | numeric | yes |  |
| `OP_2DIV` | 0x8e | 142 | numeric | yes |  |
| `OP_NEGATE` | 0x8f | 143 | numeric | yes |  |
| `OP_ABS` | 0x90 | 144 | numeric | yes |  |
| `OP_NOT` | 0x91 | 145 | numeric | yes |  |
| `OP_0NOTEQUAL` | 0x92 | 146 | numeric | yes |  |
| `OP_ADD` | 0x93 | 147 | numeric | yes |  |
| `OP_SUB` | 0x94 | 148 | numeric | yes |  |
| `OP_MUL` | 0x95 | 149 | numeric | yes |  |
| `OP_DIV` | 0x96 | 150 | numeric | yes |  |
| `OP_MOD` | 0x97 | 151 | numeric | yes |  |
| `OP_LSHIFT` | 0x98 | 152 | numeric | yes |  |
| `OP_RSHIFT` | 0x99 | 153 | numeric | yes |  |
| `OP_BOOLAND` | 0x9a | 154 | numeric | yes |  |
| `OP_BOOLOR` | 0x9b | 155 | numeric | yes |  |
| `OP_NUMEQUAL` | 0x9c | 156 | numeric | yes |  |
| `OP_NUMEQUALVERIFY` | 0x9d | 157 | numeric | yes |  |
| `OP_NUMNOTEQUAL` | 0x9e | 158 | numeric | yes |  |
| `OP_LESSTHAN` | 0x9f | 159 | numeric | yes |  |
| `OP_GREATERTHAN` | 0xa0 | 160 | numeric | yes |  |
| `OP_LESSTHANOREQUAL` | 0xa1 | 161 | numeric | yes |  |
| `OP_GREATERTHANOREQUAL` | 0xa2 | 162 | numeric | yes |  |
| `OP_MIN` | 0xa3 | 163 | numeric | yes |  |
| `OP_MAX` | 0xa4 | 164 | numeric | yes |  |
| `OP_WITHIN` | 0xa5 | 165 | numeric | yes |  |
| `OP_RIPEMD160` | 0xa6 | 166 | crypto | yes |  |
| `OP_SHA1` | 0xa7 | 167 | crypto | yes |  |
| `OP_SHA256` | 0xa8 | 168 | crypto | yes |  |
| `OP_HASH160` | 0xa9 | 169 | crypto | yes |  |
| `OP_HASH256` | 0xaa | 170 | crypto | yes |  |
| `OP_CODESEPARATOR` | 0xab | 171 | crypto | yes |  |
| `OP_CHECKSIG` | 0xac | 172 | crypto | yes |  |
| `OP_CHECKSIGVERIFY` | 0xad | 173 | crypto | yes |  |
| `OP_CHECKMULTISIG` | 0xae | 174 | crypto | yes |  |
| `OP_CHECKMULTISIGVERIFY` | 0xaf | 175 | crypto | yes |  |
| `OP_SINGLEBYTE_END` | 0xf0 | 240 | multi-byte opcodes | — |  |
| `OP_DOUBLEBYTE_BEGIN` | 0xf000 | 61440 | multi-byte opcodes | — |  |
| `OP_PUBKEY` | 0xf001 | 61441 | template matching params | — |  |
| `OP_PUBKEYHASH` | 0xf002 | 61442 | template matching params | — |  |
| `OP_INVALIDOPCODE` | 0xffff | 65535 | template matching params | — |  |

