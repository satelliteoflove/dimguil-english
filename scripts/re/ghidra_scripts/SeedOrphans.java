// Post-analysis: make functions for code that analysis didn't reach.
// Args: lo hi (hex range), then any number of overlay files.
//
// The executable's routines that only overlays call, and routines reached only through
// pointer tables, have no caller in the program, so Ghidra never starts a function there.
//   1. Every jal target in the given overlay files that lands in [lo, hi) is seeded (for
//      MAIN: the overlays' calls into the executable).
//   2. Every jr ra in [lo, hi) that no function covers gets one, starting just after the
//      nearest code before it that ends something: a jr ra + delay slot, a j + delay
//      slot followed by a prologue, zero padding,
//      or the end of an existing function.
// Repeats until no new functions appear; CleanOverlay drops any that ran into data.
// @category Dimguil
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.util.*;

public class SeedOrphans extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        long lo = Long.decode(a[0]), hi = Long.decode(a[1]) & ~3L;   // whole words only
        AddressSpace space = currentProgram.getAddressFactory().getDefaultAddressSpace();
        Memory mem = currentProgram.getMemory();
        FunctionManager fm = currentProgram.getFunctionManager();
        int made = 0;
        for (int k = 2; k < a.length; k++) {
            byte[] d = Files.readAllBytes(Paths.get(a[k]));
            for (int i = 0; i + 4 <= d.length; i += 4) {
                int x = (d[i] & 0xff) | (d[i+1] & 0xff) << 8 | (d[i+2] & 0xff) << 16 | (d[i+3] & 0xff) << 24;
                if ((x >>> 26) != 3) continue;
                long t = 0x80000000L | ((x & 0x3ffffffL) << 2);
                if (t >= lo && t < hi && make(space.getAddress(t), fm)) made++;
            }
        }
        analyzeChanges(currentProgram);
        for (int round = 0; round < 8; round++) {
            int before = made;
            for (long p = lo; p < hi; p += 4) {
                Address r = space.getAddress(p);
                if (mem.getInt(r) != 0x03e00008 || fm.getFunctionContaining(r) != null) continue;
                long s = p - 4;
                while (s >= lo) {
                    Address sa = space.getAddress(s);
                    int x = mem.getInt(sa);
                    if (x == 0) break;
                    if (s - 8 >= lo) {
                        // jr ra + delay slot ends a function; so does j + delay slot when a
                        // prologue follows (a tail call; a bare j is often an if/else jump)
                        int e = mem.getInt(space.getAddress(s - 8));
                        boolean prologue = (x >>> 16) == 0x27bd && (short) (x & 0xffff) < 0;
                        if (e == 0x03e00008 || ((e >>> 26) == 2 && prologue)) { s -= 4; break; }
                    }
                    Function f = fm.getFunctionContaining(sa);
                    if (f != null) break;
                    s -= 4;
                }
                long start = s + 4;
                while (start < p && mem.getInt(space.getAddress(start)) == 0) start += 4;
                if (make(space.getAddress(start), fm)) made++;
            }
            analyzeChanges(currentProgram);
            if (made == before) break;
        }
        println("seeded " + made + " orphan functions in " + a[0] + "-" + a[1]);
    }

    boolean make(Address at, FunctionManager fm) {
        if (fm.getFunctionAt(at) != null || fm.getFunctionContaining(at) != null) return false;
        new DisassembleCommand(at, null, true).applyTo(currentProgram, monitor);
        return new CreateFunctionCmd(at).applyTo(currentProgram, monitor) && fm.getFunctionAt(at) != null;
    }
}
