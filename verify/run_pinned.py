"""Run a script with this process pinned to one logical CPU (Windows), and report that CPU's efficiency
class as the OS reports it. Usage: python verify/run_pinned.py <cpu index> <script> [args...]"""
import ctypes
import ctypes.wintypes as wt
import runpy
import sys

cpu = int(sys.argv[1])
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetCurrentProcess.restype = wt.HANDLE
k32.SetProcessAffinityMask.argtypes = [wt.HANDLE, ctypes.c_size_t]
if not k32.SetProcessAffinityMask(k32.GetCurrentProcess(), 1 << cpu):
    raise SystemExit("affinity failed: %d" % ctypes.get_last_error())

# Efficiency class per logical processor: RelationProcessorCore = 0 records, each with EfficiencyClass
# and a group mask of its logical processors.
need = wt.DWORD(0)
k32.GetLogicalProcessorInformationEx(0, None, ctypes.byref(need))
buf = ctypes.create_string_buffer(need.value)
k32.GetLogicalProcessorInformationEx(0, buf, ctypes.byref(need))
off, cls = 0, {}
while off < need.value:
    rel = int.from_bytes(buf.raw[off:off + 4], "little")
    size = int.from_bytes(buf.raw[off + 4:off + 8], "little")
    if rel == 0:
        eff = buf.raw[off + 9]
        mask = int.from_bytes(buf.raw[off + 8 + 24:off + 8 + 32], "little")   # GROUP_AFFINITY.Mask
        for i in range(64):
            if mask >> i & 1:
                cls[i] = eff
    off += size
print("  pinned to logical CPU %d, efficiency class %s (higher = performance core); classes seen: %s"
      % (cpu, cls.get(cpu), sorted(set(cls.values()))), flush=True)
sys.argv = sys.argv[2:]
runpy.run_path(sys.argv[0], run_name="__main__")
