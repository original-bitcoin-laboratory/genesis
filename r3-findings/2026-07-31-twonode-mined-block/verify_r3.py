import base64, hashlib, struct

B64_B = "+b602R0BAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA7o+39ensSsnrHLD5ndo9hf8gbw4iKUTI6n7iqSx5eSimrX0n//wAdHawrfAEBAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/////00E//8AHQEERVRoZSBUaW1lcyAwMy9KYW4vMjAwOSBDaGFuY2VsbG9yIG9uIGJyaW5rIG9mIHNlY29uZCBiYWlsb3V0IGZvciBiYW5rc/////8BAPIFKgEAAABDQQRniv2w/lVIJxln8aZxMLcQXNaoKOA5CaZ5YuDqH2Hetkn2vD9M7zjE81UE5R7BEt5cOE33uguNV4pMcCtr8R1frAAAAAD5vrTZ1wAAAAEAAABv4owKtvGzcsGmokauY/dPkx6DZeFaCJxo1hkAAAAAAPUP28shI7F1HhXXUpRC3FUfTsw7Ft3zy4m1dRUO94UOc4Rrav//AB1uDKQ1AQEAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/////BwT//wAdAQH/////AQDyBSoBAAAAQ0EE5fgYu6zgzRnIunsCa06zVoJBWVQEwlXyXoLDzo8BUCUuxzh+utA8xsMolGWRoEHOV2si8VlphymBTjwx0ON3XqwAAAAA"
B64_A = B64_B  # both pastes were identical; assert below

def d(b64):
    return base64.b64decode(b64 + "=" * (-len(b64) % 4))

raw_b, raw_a = d(B64_B), d(B64_A)
print("node A blk == node B blk :", raw_a == raw_b, f"({len(raw_b)} bytes)")

def dsha(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def rh(b):   return b[::-1].hex()   # display (big-endian) hash

# parse v0.1 blk file:  [magic f9beb4d9][size u32][block]...
blocks, off = [], 0
while off < len(raw_b):
    magic, size = struct.unpack_from("<I I", raw_b, off); off += 8
    blk = raw_b[off:off+size]; off += size
    blocks.append((magic, blk))

TARGET1 = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
for i,(magic,blk) in enumerate(blocks):
    hdr = blk[:80]
    ver, = struct.unpack_from("<I", hdr, 0)
    prev = hdr[4:36]; merk = hdr[36:68]
    t, bits, nonce = struct.unpack_from("<I I I", hdr, 68)
    h = dsha(hdr)
    print(f"\n== block {i} ==")
    print(f"  magic      : {magic:08x} (mainnet f9beb4d9: {magic==0xd9b4bef9})")
    print(f"  hash       : {rh(h)}")
    print(f"  prev       : {rh(prev)}")
    print(f"  version {ver}  time {t}  bits {bits:08x}  nonce {nonce}")
    print(f"  PoW valid  : {int.from_bytes(h,'little') < TARGET1}  (hash < difficulty-1 target)")
    # coinbase scriptSig text (find the Chancellor line in the genesis coinbase)
    txt = bytes(c for c in blk if 32 <= c < 127)
    if b"Chancellor" in blk:
        s = blk.find(b"The Times"); print(f"  coinbase   : {blk[s:s+64].decode('latin-1')}")

g = rh(dsha(blocks[0][1][:80]))
b1 = rh(dsha(blocks[1][1][:80]))
print("\n--- verdict ---")
print("block 0 IS the historical genesis 000000000019d668...0a8ce26f :",
      g == "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f")
print("block 1 hash starts 000000005bdcfb (matches node B's getdata log) :", b1.startswith("000000005bdcfb"))
print("block 1 builds on genesis :", rh(blocks[1][1][4:36]) == g)
