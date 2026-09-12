//! miner <prefix76_hex> <nbits_hex> [start_nonce] [threads]
//!
//! Prints the first nonce >= start whose header double-SHA-256, as a little-endian 256-bit integer,
//! is at or below the target encoded by nBits, or `none` if the 32-bit nonce space is exhausted.
//! Dependency-free. SHA-256 is implemented twice: a portable FIPS 180-4 compression, and the same
//! function on the x86 SHA extensions (SHA-NI), chosen at runtime. The midstate of the first 64
//! header bytes is computed once; each nonce then costs two compressions. Threads take interleaved
//! nonce stripes. The two implementations are cross-checked at start-up on a known answer. NOT money.

use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread;

const K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];
const H0: [u32; 8] = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
];

// ------------------------------------------------------------------------------------------------
// portable compression
// ------------------------------------------------------------------------------------------------

#[inline(always)]
fn compress_portable(state: &mut [u32; 8], block: &[u8; 64]) {
    let mut w = [0u32; 64];
    for i in 0..16 {
        w[i] = u32::from_be_bytes([block[4 * i], block[4 * i + 1], block[4 * i + 2], block[4 * i + 3]]);
    }
    for i in 16..64 {
        let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
        let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16].wrapping_add(s0).wrapping_add(w[i - 7]).wrapping_add(s1);
    }
    let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h) =
        (state[0], state[1], state[2], state[3], state[4], state[5], state[6], state[7]);
    for i in 0..64 {
        let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
        let ch = (e & f) ^ (!e & g);
        let t1 = h.wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
        let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
        let maj = (a & b) ^ (a & c) ^ (b & c);
        let t2 = s0.wrapping_add(maj);
        h = g; g = f; f = e; e = d.wrapping_add(t1); d = c; c = b; b = a; a = t1.wrapping_add(t2);
    }
    state[0] = state[0].wrapping_add(a); state[1] = state[1].wrapping_add(b);
    state[2] = state[2].wrapping_add(c); state[3] = state[3].wrapping_add(d);
    state[4] = state[4].wrapping_add(e); state[5] = state[5].wrapping_add(f);
    state[6] = state[6].wrapping_add(g); state[7] = state[7].wrapping_add(h);
}

// ------------------------------------------------------------------------------------------------
// SHA-NI compression (x86_64 with the `sha` feature); same function, hardware rounds
// ------------------------------------------------------------------------------------------------

#[cfg(target_arch = "x86_64")]
mod shani {
    use super::K;
    use core::arch::x86_64::*;

    #[target_feature(enable = "sha,sse4.1,ssse3")]
    pub unsafe fn compress(state: &mut [u32; 8], block: &[u8; 64]) {
        let mask = _mm_set_epi64x(0x0c0d0e0f08090a0bu64 as i64, 0x0405060700010203u64 as i64);
        let mut tmp = _mm_loadu_si128(state.as_ptr() as *const __m128i);
        let mut state1 = _mm_loadu_si128(state.as_ptr().add(4) as *const __m128i);
        tmp = _mm_shuffle_epi32::<0xB1>(tmp);                 // CDAB
        state1 = _mm_shuffle_epi32::<0x1B>(state1);           // EFGH
        let mut state0 = _mm_alignr_epi8::<8>(tmp, state1);   // ABEF
        state1 = _mm_blend_epi16::<0xF0>(state1, tmp);        // CDGH
        let abef_save = state0;
        let cdgh_save = state1;

        let mut msg = [_mm_setzero_si128(); 4];
        for j in 0..16usize {
            if j < 4 {
                let m = _mm_loadu_si128(block.as_ptr().add(16 * j) as *const __m128i);
                msg[j] = _mm_shuffle_epi8(m, mask);
            }
            let kv = _mm_set_epi32(K[4 * j + 3] as i32, K[4 * j + 2] as i32, K[4 * j + 1] as i32, K[4 * j] as i32);
            let mut m = _mm_add_epi32(msg[j % 4], kv);
            state1 = _mm_sha256rnds2_epu32(state1, state0, m);
            if (3..=14).contains(&j) {
                let t = _mm_alignr_epi8::<4>(msg[j % 4], msg[(j + 3) % 4]);
                let n = (j + 1) % 4;
                msg[n] = _mm_add_epi32(msg[n], t);
                msg[n] = _mm_sha256msg2_epu32(msg[n], msg[j % 4]);
            }
            m = _mm_shuffle_epi32::<0x0E>(m);
            state0 = _mm_sha256rnds2_epu32(state0, state1, m);
            if (1..=12).contains(&j) {
                let p = (j + 3) % 4;
                msg[p] = _mm_sha256msg1_epu32(msg[p], msg[j % 4]);
            }
        }
        state0 = _mm_add_epi32(state0, abef_save);
        state1 = _mm_add_epi32(state1, cdgh_save);
        tmp = _mm_shuffle_epi32::<0x1B>(state0);              // FEBA
        state1 = _mm_shuffle_epi32::<0xB1>(state1);           // DCHG
        state0 = _mm_blend_epi16::<0xF0>(tmp, state1);        // DCBA
        state1 = _mm_alignr_epi8::<8>(state1, tmp);           // HGFE
        _mm_storeu_si128(state.as_mut_ptr() as *mut __m128i, state0);
        _mm_storeu_si128(state.as_mut_ptr().add(4) as *mut __m128i, state1);
    }
}

fn have_shani() -> bool {
    #[cfg(target_arch = "x86_64")]
    { std::arch::is_x86_feature_detected!("sha") && std::arch::is_x86_feature_detected!("sse4.1") }
    #[cfg(not(target_arch = "x86_64"))]
    { false }
}

#[inline(always)]
fn compress(state: &mut [u32; 8], block: &[u8; 64], hw: bool) {
    #[cfg(target_arch = "x86_64")]
    {
        if hw { unsafe { shani::compress(state, block) }; return; }
    }
    let _ = hw;
    compress_portable(state, block);
}

fn state_bytes(s: &[u32; 8]) -> [u8; 32] {
    let mut out = [0u8; 32];
    for i in 0..8 { out[4 * i..4 * i + 4].copy_from_slice(&s[i].to_be_bytes()); }
    out
}

/// Double SHA-256 of an 80-byte header given the midstate of its first 64 bytes and the last 16 bytes
/// (of which the final 4 are the nonce).
#[inline(always)]
fn header_hash(midstate: &[u32; 8], tail16: &[u8; 16], hw: bool) -> [u8; 32] {
    let mut blk = [0u8; 64];
    blk[..16].copy_from_slice(tail16);
    blk[16] = 0x80;
    blk[62] = 0x02; blk[63] = 0x80;              // bit length 640 = 0x0280
    let mut s = *midstate;
    compress(&mut s, &blk, hw);
    let first = state_bytes(&s);
    let mut blk2 = [0u8; 64];
    blk2[..32].copy_from_slice(&first);
    blk2[32] = 0x80;
    blk2[62] = 0x01;                              // bit length 256 = 0x0100
    let mut s2 = H0;
    compress(&mut s2, &blk2, hw);
    state_bytes(&s2)
}

fn sha256(data: &[u8], hw: bool) -> [u8; 32] {
    let mut s = H0;
    let mut padded = data.to_vec();
    padded.push(0x80);
    while padded.len() % 64 != 56 { padded.push(0); }
    padded.extend_from_slice(&((data.len() as u64) * 8).to_be_bytes());
    for chunk in padded.chunks(64) {
        let mut b = [0u8; 64];
        b.copy_from_slice(chunk);
        compress(&mut s, &b, hw);
    }
    state_bytes(&s)
}

/// hash (little-endian 256-bit) <= target (as 32 big-endian bytes) ?
#[inline(always)]
fn meets(hash: &[u8; 32], target_be: &[u8; 32]) -> bool {
    for i in 0..32 {
        let h = hash[31 - i];
        let t = target_be[i];
        if h < t { return true; }
        if h > t { return false; }
    }
    true
}

fn target_from_nbits(nbits: u32) -> [u8; 32] {
    let size = (nbits >> 24) as usize;
    let word = nbits & 0x007f_ffff;
    let mut t = [0u8; 32];
    if size <= 3 {
        let v = word >> (8 * (3 - size));
        t[29..32].copy_from_slice(&v.to_be_bytes()[1..]);
    } else {
        let start = 32 - size;
        let wb = word.to_be_bytes();
        for i in 0..3 { if start + i < 32 { t[start + i] = wb[i + 1]; } }
    }
    t
}

fn hex(s: &str) -> Vec<u8> {
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).expect("hex")).collect()
}

fn hexstr(b: &[u8]) -> String { b.iter().map(|x| format!("{:02x}", x)).collect() }

fn selftest(hw: bool) {
    // FIPS 180-4 known answer, both paths
    let abc = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    assert_eq!(hexstr(&sha256(b"abc", false)), abc, "portable SHA-256 KAT failed");
    if hw { assert_eq!(hexstr(&sha256(b"abc", true)), abc, "SHA-NI SHA-256 KAT failed"); }
    // a two-block message exercises the schedule carry between compressions
    let msg = b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    let want = "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1";
    assert_eq!(hexstr(&sha256(msg, false)), want);
    if hw { assert_eq!(hexstr(&sha256(msg, true)), want); }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: miner <prefix76_hex> <nbits_hex> [start_nonce] [threads]");
        std::process::exit(2);
    }
    let hw = have_shani() && std::env::var("MINER_NO_SHANI").is_err();
    selftest(hw);
    let prefix = hex(&args[1]);
    assert_eq!(prefix.len(), 76, "prefix must be 76 bytes");
    let nbits = u32::from_str_radix(args[2].trim_start_matches("0x"), 16).expect("nbits");
    let start: u64 = args.get(3).map(|s| s.parse().unwrap()).unwrap_or(0);
    let mut threads: usize = args.get(4).map(|s| s.parse().unwrap()).unwrap_or(0);
    if threads == 0 { threads = thread::available_parallelism().map(|n| n.get()).unwrap_or(4); }
    eprintln!("miner: {} threads, {}", threads, if hw { "SHA-NI" } else { "portable SHA-256" });

    let mut mid = H0;
    let mut first64 = [0u8; 64];
    first64.copy_from_slice(&prefix[..64]);
    compress(&mut mid, &first64, hw);
    let mut tail = [0u8; 16];
    tail[..12].copy_from_slice(&prefix[64..76]);
    let target = target_from_nbits(nbits);

    let found = Arc::new(AtomicBool::new(false));
    let answer = Arc::new(AtomicU64::new(u64::MAX));
    let mut handles = Vec::new();
    for t in 0..threads {
        let (found, answer) = (found.clone(), answer.clone());
        handles.push(thread::spawn(move || {
            let mut tail = tail;
            let mut nonce = start + t as u64;
            let mut i: u32 = 0;
            while nonce < (1u64 << 32) {
                tail[12..16].copy_from_slice(&(nonce as u32).to_le_bytes());
                let h = header_hash(&mid, &tail, hw);
                if meets(&h, &target) {
                    answer.fetch_min(nonce, Ordering::SeqCst);
                    found.store(true, Ordering::SeqCst);
                    return;
                }
                nonce += threads as u64;
                i = i.wrapping_add(1);
                if i & 0xffff == 0 && found.load(Ordering::Relaxed) { return; }
            }
        }));
    }
    for h in handles { h.join().unwrap(); }
    let a = answer.load(Ordering::SeqCst);
    if a == u64::MAX { println!("none"); } else { println!("{}", a); }
}
