//! A faithful port of the v0.1 `EvalScript` (script.cpp) — the full opcode machine — operating on
//! raw CScript **bytes**. NOT money.
//!
//! Mirrors the lab's `model/evalscript_model.py` (and thus script.cpp): the `bignum.h` number codec
//! (sign-magnitude little-endian, **unbounded** — v0.1 had no CScriptNum size limit), push / control
//! flow (`vfExec`) / stack / alt-stack / splice / bitwise / numeric / hash opcodes, `OP_CODESEPARATOR`,
//! and `OP_CHECKSIG(VERIFY)` / `OP_CHECKMULTISIG(VERIFY)` (via a `SigCheck`). `run` returns `(ok,
//! stack)`; `ok` is false only on the structural `return false` paths (underflow, bad opcode, bad IF
//! nesting, div-by-zero, …). Like v0.1 it does **not** reject an unterminated `OP_IF`.

use num_bigint::{BigInt, Sign};
use num_traits::{Signed, ToPrimitive, Zero};
use ripemd::Ripemd160;
use sha1::{Digest, Sha1};

use crate::{dsha256, sha256};

/// Signature checking for `OP_CHECKSIG` / `OP_CHECKMULTISIG` (`subscript` is the scriptCode).
pub trait SigCheck {
    fn check_sig(&self, sig: &[u8], pubkey: &[u8], subscript: &[u8]) -> bool;
}

// ---- number codec (bignum.h getvch/setvch; sign-magnitude LE) --------------------

pub fn bn_from_vch(vch: &[u8]) -> BigInt {
    if vch.is_empty() {
        return BigInt::zero();
    }
    let mut b = vch.to_vec();
    let last = b.len() - 1;
    let neg = b[last] & 0x80 != 0;
    b[last] &= 0x7f;
    let mag = BigInt::from_bytes_le(Sign::Plus, &b);
    if neg {
        -mag
    } else {
        mag
    }
}

pub fn bn_to_vch(n: &BigInt) -> Vec<u8> {
    if n.is_zero() {
        return vec![];
    }
    let neg = n.sign() == Sign::Minus;
    let (_, mut b) = n.to_bytes_le(); // magnitude, little-endian
    let last = b.len() - 1;
    if b[last] & 0x80 != 0 {
        b.push(if neg { 0x80 } else { 0x00 });
    } else if neg {
        b[last] |= 0x80;
    }
    b
}

pub fn cast_to_bool(vch: &[u8]) -> bool {
    !bn_from_vch(vch).is_zero()
}

fn get_int(vch: &[u8]) -> i64 {
    let n = bn_from_vch(vch);
    if n > BigInt::from(0x7fff_ffffi64) {
        0x7fff_ffff
    } else if n < BigInt::from(-0x8000_0000i64) {
        -0x8000_0000
    } else {
        n.to_i64().unwrap()
    }
}

fn sign_i(n: &BigInt) -> i64 {
    match n.sign() {
        Sign::Minus => -1,
        Sign::NoSign => 0,
        Sign::Plus => 1,
    }
}

// ---- byte-level opcode iteration (script.h GetOp) --------------------------------

struct Op {
    start: usize,
    end: usize,
    op: u8,
    data: Option<Vec<u8>>,
}

fn tokenize(script: &[u8]) -> Vec<Op> {
    let mut ops = Vec::new();
    let n = script.len();
    let mut pc = 0;
    while pc < n {
        let start = pc;
        let op = script[pc];
        pc += 1;
        let mut data = None;
        if op <= 78 {
            let size;
            if op < 76 {
                size = op as usize;
            } else if op == 76 {
                if pc + 1 > n {
                    break;
                }
                size = script[pc] as usize;
                pc += 1;
            } else if op == 77 {
                if pc + 2 > n {
                    break;
                }
                size = script[pc] as usize | ((script[pc + 1] as usize) << 8);
                pc += 2;
            } else {
                if pc + 4 > n {
                    break;
                }
                size = u32::from_le_bytes(script[pc..pc + 4].try_into().unwrap()) as usize;
                pc += 4;
            }
            if pc + size > n {
                break;
            }
            data = Some(script[pc..pc + size].to_vec());
            pc += size;
        }
        ops.push(Op { start, end: pc, op, data });
    }
    ops
}

fn push_data(data: &[u8]) -> Vec<u8> {
    let n = data.len();
    let mut out = Vec::new();
    if n < 76 {
        out.push(n as u8);
    } else if n <= 0xff {
        out.push(76);
        out.push(n as u8);
    } else {
        out.push(77);
        out.push((n & 0xff) as u8);
        out.push(((n >> 8) & 0xff) as u8);
    }
    out.extend_from_slice(data);
    out
}

/// CScript::FindAndDelete — remove each opcode chunk equal to `needle`.
fn find_and_delete(script: &[u8], needle: &[u8]) -> Vec<u8> {
    if needle.is_empty() {
        return script.to_vec();
    }
    let mut out = Vec::new();
    for o in tokenize(script) {
        let chunk = &script[o.start..o.end];
        if chunk != needle {
            out.extend_from_slice(chunk);
        }
    }
    out
}

fn hash_op(op: u8, data: &[u8]) -> Vec<u8> {
    match op {
        167 => Sha1::digest(data).to_vec(),                                  // OP_SHA1
        168 => sha256(data).to_vec(),                                        // OP_SHA256
        170 => dsha256(data).to_vec(),                                       // OP_HASH256
        166 => Ripemd160::digest(data).to_vec(),                             // OP_RIPEMD160
        169 => Ripemd160::digest(sha256(data)).to_vec(),                     // OP_HASH160
        _ => unreachable!(),
    }
}

/// Execute `script`. Returns `(ok, stack)` — see the module doc.
pub fn run(script: &[u8], checker: Option<&dyn SigCheck>) -> (bool, Vec<Vec<u8>>) {
    let ops = tokenize(script);
    let mut stack: Vec<Vec<u8>> = Vec::new();
    let mut altstack: Vec<Vec<u8>> = Vec::new();
    let mut vfexec: Vec<bool> = Vec::new();
    let mut codesep: usize = 0; // byte offset just after the most recent OP_CODESEPARATOR

    macro_rules! need {
        ($k:expr) => {
            if stack.len() < $k {
                return (false, stack);
            }
        };
    }
    macro_rules! aneed {
        ($k:expr) => {
            if altstack.len() < $k {
                return (false, stack);
            }
        };
    }

    for o in &ops {
        let op = o.op;
        let fexec = vfexec.iter().all(|&b| b);
        let is_ifelse = matches!(op, 99 | 100 | 103 | 104);
        if fexec {
            if let Some(d) = &o.data {
                stack.push(d.clone());
                continue;
            }
        }
        if !(fexec || is_ifelse) {
            continue;
        }
        // push-number opcodes: OP_1NEGATE, OP_1..OP_16
        if matches!(op, 79 | 81..=96) {
            let v: i64 = if op == 79 { -1 } else { op as i64 - 80 };
            stack.push(bn_to_vch(&BigInt::from(v)));
            continue;
        }
        match op {
            97 => {} // OP_NOP
            // ---- control ----
            99 | 100 => {
                // OP_IF / OP_NOTIF
                let mut v = false;
                if fexec {
                    need!(1);
                    v = cast_to_bool(&stack.pop().unwrap());
                    if op == 100 {
                        v = !v;
                    }
                }
                vfexec.push(v);
            }
            103 => {
                // OP_ELSE
                if vfexec.is_empty() {
                    return (false, stack);
                }
                let last = vfexec.len() - 1;
                vfexec[last] = !vfexec[last];
            }
            104 => {
                // OP_ENDIF
                if vfexec.is_empty() {
                    return (false, stack);
                }
                vfexec.pop();
            }
            105 => {
                // OP_VERIFY
                need!(1);
                if !cast_to_bool(stack.last().unwrap()) {
                    return (true, stack); // leave false on top
                }
                stack.pop();
            }
            106 => return (true, stack), // OP_RETURN
            171 => codesep = o.end,       // OP_CODESEPARATOR
            // ---- stack / alt-stack ----
            107 => {
                need!(1);
                altstack.push(stack.pop().unwrap());
            }
            108 => {
                aneed!(1);
                stack.push(altstack.pop().unwrap());
            }
            109 => {
                need!(2);
                stack.pop();
                stack.pop();
            }
            110 => {
                need!(2);
                let n = stack.len();
                let (a, b) = (stack[n - 2].clone(), stack[n - 1].clone());
                stack.push(a);
                stack.push(b);
            }
            111 => {
                need!(3);
                let n = stack.len();
                let (a, b, c) = (stack[n - 3].clone(), stack[n - 2].clone(), stack[n - 1].clone());
                stack.push(a);
                stack.push(b);
                stack.push(c);
            }
            112 => {
                need!(4);
                let n = stack.len();
                let (a, b) = (stack[n - 4].clone(), stack[n - 3].clone());
                stack.push(a);
                stack.push(b);
            }
            113 => {
                // OP_2ROT: move the 3rd pair to the top
                need!(6);
                let n = stack.len();
                let a: Vec<Vec<u8>> = stack.split_off(n - 6);
                stack.extend_from_slice(&a[2..]);
                stack.extend_from_slice(&a[..2]);
            }
            114 => {
                // OP_2SWAP
                need!(4);
                let n = stack.len();
                stack.swap(n - 4, n - 2);
                stack.swap(n - 3, n - 1);
            }
            115 => {
                // OP_IFDUP
                need!(1);
                if cast_to_bool(stack.last().unwrap()) {
                    stack.push(stack.last().unwrap().clone());
                }
            }
            116 => stack.push(bn_to_vch(&BigInt::from(stack.len() as i64))), // OP_DEPTH
            117 => {
                need!(1);
                stack.pop();
            }
            118 => {
                need!(1);
                stack.push(stack.last().unwrap().clone());
            }
            119 => {
                // OP_NIP
                need!(2);
                let n = stack.len();
                stack.remove(n - 2);
            }
            120 => {
                need!(2);
                stack.push(stack[stack.len() - 2].clone());
            }
            121 | 122 => {
                // OP_PICK / OP_ROLL
                need!(1);
                let n = get_int(&stack.pop().unwrap());
                if n < 0 || n as usize >= stack.len() {
                    return (false, stack);
                }
                let idx = stack.len() - 1 - n as usize;
                let v = stack[idx].clone();
                if op == 122 {
                    stack.remove(idx);
                }
                stack.push(v);
            }
            123 => {
                // OP_ROT
                need!(3);
                let n = stack.len();
                stack.swap(n - 3, n - 2);
                stack.swap(n - 2, n - 1);
            }
            124 => {
                // OP_SWAP
                need!(2);
                let n = stack.len();
                stack.swap(n - 2, n - 1);
            }
            125 => {
                // OP_TUCK
                need!(2);
                let n = stack.len();
                let v = stack[n - 1].clone();
                stack.insert(n - 2, v);
            }
            // ---- splice ----
            126 => {
                // OP_CAT
                need!(2);
                let b = stack.pop().unwrap();
                stack.last_mut().unwrap().extend_from_slice(&b);
            }
            127 => {
                // OP_SUBSTR
                need!(3);
                let size = get_int(&stack.pop().unwrap());
                let begin = get_int(&stack.pop().unwrap());
                let vch = stack.pop().unwrap();
                let end = begin + size;
                if begin < 0 || end < begin {
                    return (false, stack);
                }
                let b = (begin as usize).min(vch.len());
                let e = (end as usize).min(vch.len());
                stack.push(vch[b..e].to_vec());
            }
            128 | 129 => {
                // OP_LEFT / OP_RIGHT
                need!(2);
                let size = get_int(&stack.pop().unwrap());
                let vch = stack.pop().unwrap();
                if size < 0 {
                    return (false, stack);
                }
                let s = (size as usize).min(vch.len());
                stack.push(if op == 128 { vch[..s].to_vec() } else { vch[vch.len() - s..].to_vec() });
            }
            130 => {
                // OP_SIZE
                need!(1);
                let len = stack.last().unwrap().len();
                stack.push(bn_to_vch(&BigInt::from(len as i64)));
            }
            // ---- bitwise ----
            131 => {
                // OP_INVERT
                need!(1);
                let v = stack.pop().unwrap();
                stack.push(v.iter().map(|x| !x).collect());
            }
            132 | 133 | 134 => {
                // OP_AND / OP_OR / OP_XOR
                need!(2);
                let b = stack.pop().unwrap();
                let a = stack.pop().unwrap();
                let n = a.len().max(b.len());
                let mut out = vec![0u8; n];
                for i in 0..n {
                    let (x, y) = (*a.get(i).unwrap_or(&0), *b.get(i).unwrap_or(&0));
                    out[i] = match op {
                        132 => x & y,
                        133 => x | y,
                        _ => x ^ y,
                    };
                }
                stack.push(out);
            }
            135 | 136 => {
                // OP_EQUAL / OP_EQUALVERIFY
                need!(2);
                let b = stack.pop().unwrap();
                let a = stack.pop().unwrap();
                let eq = a == b;
                stack.push(if eq { vec![1] } else { vec![] });
                if op == 136 {
                    if eq {
                        stack.pop();
                    } else {
                        return (true, stack);
                    }
                }
            }
            // ---- numeric (unary) ----
            139 | 140 | 141 | 142 | 143 | 144 | 145 | 146 => {
                need!(1);
                let n = bn_from_vch(&stack.pop().unwrap());
                let r = match op {
                    139 => n + BigInt::from(1),
                    140 => n - BigInt::from(1),
                    141 => n * BigInt::from(2),
                    142 => BigInt::from(sign_i(&n)) * (n.abs() >> 1usize),
                    143 => -n,
                    144 => n.abs(),
                    145 => BigInt::from(n.is_zero() as i64),
                    _ => BigInt::from(!n.is_zero() as i64), // OP_0NOTEQUAL
                };
                stack.push(bn_to_vch(&r));
            }
            // ---- numeric (binary) ----
            147..=164 => {
                need!(2);
                let b = bn_from_vch(&stack.pop().unwrap());
                let a = bn_from_vch(&stack.pop().unwrap());
                if (op == 150 || op == 151) && b.is_zero() {
                    return (false, stack); // OP_DIV / OP_MOD by zero
                }
                if (op == 152 || op == 153) && b.sign() == Sign::Minus {
                    return (false, stack); // OP_LSHIFT / OP_RSHIFT by negative
                }
                let bo = |x: bool| BigInt::from(x as i64);
                let r = match op {
                    147 => a + b,
                    148 => a - b,
                    149 => a * b,
                    150 => BigInt::from(sign_i(&a) * sign_i(&b)) * (a.abs() / b.abs()),
                    151 => BigInt::from(sign_i(&a)) * (a.abs() % b.abs()),
                    152 => match b.to_usize() {
                        Some(sh) => BigInt::from(sign_i(&a)) * (a.abs() << sh),
                        None => return (false, stack),
                    },
                    153 => match b.to_usize() {
                        Some(sh) => BigInt::from(sign_i(&a)) * (a.abs() >> sh),
                        None => return (false, stack),
                    },
                    154 => bo(!a.is_zero() && !b.is_zero()),
                    155 => bo(!a.is_zero() || !b.is_zero()),
                    156 | 157 => bo(a == b), // NUMEQUAL / NUMEQUALVERIFY
                    158 => bo(a != b),
                    159 => bo(a < b),
                    160 => bo(a > b),
                    161 => bo(a <= b),
                    162 => bo(a >= b),
                    163 => a.min(b),
                    _ => a.max(b), // OP_MAX (164)
                };
                stack.push(bn_to_vch(&r));
                if op == 157 {
                    // OP_NUMEQUALVERIFY
                    if cast_to_bool(stack.last().unwrap()) {
                        stack.pop();
                    } else {
                        return (true, stack);
                    }
                }
            }
            165 => {
                // OP_WITHIN
                need!(3);
                let mx = bn_from_vch(&stack.pop().unwrap());
                let mn = bn_from_vch(&stack.pop().unwrap());
                let x = bn_from_vch(&stack.pop().unwrap());
                stack.push(if mn <= x && x < mx { vec![1] } else { vec![] });
            }
            // ---- hashes ----
            166 | 167 | 168 | 169 | 170 => {
                need!(1);
                let v = stack.pop().unwrap();
                stack.push(hash_op(op, &v));
            }
            // ---- signatures ----
            172 | 173 => {
                // OP_CHECKSIG / OP_CHECKSIGVERIFY
                let checker = match checker {
                    Some(c) => c,
                    None => return (false, stack),
                };
                need!(2);
                let pub_ = stack.pop().unwrap();
                let sig = stack.pop().unwrap();
                let sub = find_and_delete(&script[codesep..], &push_data(&sig));
                let ok = checker.check_sig(&sig, &pub_, &sub);
                stack.push(if ok { vec![1] } else { vec![] });
                if op == 173 {
                    if ok {
                        stack.pop();
                    } else {
                        return (true, stack);
                    }
                }
            }
            174 | 175 => {
                // OP_CHECKMULTISIG / OP_CHECKMULTISIGVERIFY
                let checker = match checker {
                    Some(c) => c,
                    None => return (false, stack),
                };
                let ok = match checkmultisig(&mut stack, checker, &script[codesep..]) {
                    Some(v) => v,
                    None => return (false, stack),
                };
                stack.push(if ok { vec![1] } else { vec![] });
                if op == 175 {
                    if ok {
                        stack.pop();
                    } else {
                        return (true, stack);
                    }
                }
            }
            _ => return (false, stack), // unsupported / disabled opcode
        }
    }
    (true, stack)
}

/// `[dummy] sig..sig <m> pub..pub <n> -- bool`, replicating v0.1's off-by-one extra pop.
fn checkmultisig(stack: &mut Vec<Vec<u8>>, checker: &dyn SigCheck, subscript: &[u8]) -> Option<bool> {
    let mut i = 1usize;
    if stack.len() < i {
        return None;
    }
    let nkeys = get_int(&stack[stack.len() - i]);
    if nkeys < 0 {
        return None;
    }
    let nkeys = nkeys as usize;
    let ikey = i + 1;
    i = ikey + nkeys;
    if stack.len() < i {
        return None;
    }
    let nsigs = get_int(&stack[stack.len() - i]);
    if nsigs < 0 || nsigs as usize > nkeys {
        return None;
    }
    let nsigs = nsigs as usize;
    let isig = i + 1;
    i = isig + nsigs;
    if stack.len() < i {
        return None;
    }
    let len = stack.len();
    let keys: Vec<Vec<u8>> = (0..nkeys).map(|k| stack[len - (ikey + k)].clone()).collect();
    let sigs: Vec<Vec<u8>> = (0..nsigs).map(|s| stack[len - (isig + s)].clone()).collect();
    let mut sc = subscript.to_vec();
    for s in &sigs {
        sc = find_and_delete(&sc, &push_data(s));
    }
    let mut success = true;
    let (mut si, mut ki) = (0usize, 0usize);
    let mut remaining = nsigs;
    while success && remaining > 0 {
        if checker.check_sig(&sigs[si], &keys[ki], &sc) {
            si += 1;
            remaining -= 1;
        }
        ki += 1;
        if remaining > nkeys - ki {
            success = false;
        }
    }
    stack.truncate(len - i); // pop nsigs+nkeys+2 + the off-by-one
    Some(success)
}

/// VerifyScript-style predicate: ran without structural error and leaves a true top-of-stack.
pub fn valid(script: &[u8], checker: Option<&dyn SigCheck>) -> bool {
    let (ok, stack) = run(script, checker);
    ok && stack.last().map(|v| cast_to_bool(v)).unwrap_or(false)
}
