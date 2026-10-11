// Post-script: map an overlay file into the PSX program at 0x800a1000, seed functions in
// it and analyze them. Args: overlay file path, module name, and optionally an underlay
// file and its module name: the larger overlay whose tail stays in RAM past this one's
// end and that this one calls into (BATTLE runs on MAZE's tail, HAZURE on JOUKA's).
// The underlay's bytes from this overlay's end to its own end are mapped as UNDER_<mod>.
//
// It runs after the executable has been analyzed with the overlay window unmapped. If the
// overlay were mapped first, Ghidra would follow every call the executable makes into any
// overlay and start a function at each target; a target meant for another overlay can be
// the middle of a function in this one, which then gets cut short (MCARD's 0x800c76f0
// split Balbo's talk handler at 0x800c7264). The placeholder functions those calls left
// in the unmapped window are deleted before mapping.
//
// Every Dimguil overlay (MAZE, BATTLE, MCARD, JOUKA, HAZURE, CMAIN, CMENU) loads at
// 0x800a1000 over the uninitialized RAM block the PSX loader makes above the executable's
// .bss. Overlays start with data, not code, so functions are seeded from:
//   - jal targets inside the overlay, from the overlay itself and from the main executable
//     (the executable calls overlay routines at fixed addresses)
//   - function prologues: addiu sp,sp,-N right after a jr ra or j + delay slot, or padding
// A seed is kept only if it looks like a function start (a prologue, or the word before it
// ends a function), so a jal into another overlay's layout doesn't plant junk.
// @category Dimguil
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.util.*;

public class LoadOverlay extends GhidraScript {
    static final long BASE = 0x800a1000L;

    @Override
    public void run() throws Exception {
        String path = getScriptArgs()[0];
        String module = getScriptArgs()[1];
        byte[] data = Files.readAllBytes(Paths.get(path));
        Memory mem = currentProgram.getMemory();
        AddressSpace space = currentProgram.getAddressFactory().getDefaultAddressSpace();
        Address start = space.getAddress(BASE);
        Address end = start.add(data.length);   // first address after the overlay

        byte[] under = getScriptArgs().length > 3 ? Files.readAllBytes(Paths.get(getScriptArgs()[2])) : null;
        Address uend = under != null && under.length > data.length ? start.add(under.length) : end;
        int removed = 0;
        for (var f : currentProgram.getFunctionManager().getFunctions(new AddressSet(start, uend.subtract(1)), true)) {
            currentProgram.getFunctionManager().removeFunction(f.getEntryPoint()); removed++;
        }
        println("removed " + removed + " placeholder functions from the overlay window");

        MemoryBlock ram = mem.getBlock(start);
        if (ram.getStart().compareTo(start) < 0) { mem.split(ram, start); ram = mem.getBlock(start); }
        if (ram.getEnd().compareTo(end) >= 0) mem.split(ram, end);
        ram = mem.getBlock(start);
        MemoryBlock ovl = mem.convertToInitialized(ram, (byte) 0);
        ovl.setName("OVL_" + module);
        ovl.setPermissions(true, true, true);
        mem.setBytes(start, data);
        println("mapped " + module + " " + start + "-" + end.subtract(1));
        if (uend.compareTo(end) > 0) {
            MemoryBlock rest = mem.getBlock(end);
            if (rest.getEnd().compareTo(uend) >= 0) mem.split(rest, uend);
            MemoryBlock ub = mem.convertToInitialized(mem.getBlock(end), (byte) 0);
            ub.setName("UNDER_" + getScriptArgs()[3]);
            ub.setPermissions(true, true, true);
            mem.setBytes(end, java.util.Arrays.copyOfRange(under, data.length, under.length));
            println("mapped " + getScriptArgs()[3] + "'s tail under it, " + end + "-" + uend.subtract(1));
        }

        // seeds
        TreeSet<Long> seeds = new TreeSet<>();
        long lo = BASE, hi = BASE + data.length;
        int n = data.length / 4;
        int[] w = new int[n];
        for (int i = 0; i < n; i++)
            w[i] = (data[4*i] & 0xff) | (data[4*i+1] & 0xff) << 8 | (data[4*i+2] & 0xff) << 16 | (data[4*i+3] & 0xff) << 24;
        // jal targets from the overlay itself
        for (int x : w) if ((x >>> 26) == 3) { long t = 0x80000000L | ((x & 0x3ffffffL) << 2); if (t >= lo && t < hi) seeds.add(t); }
        // jal targets from the executable's .text
        MemoryBlock text = mem.getBlock(".text");
        for (Address a = text.getStart(); a.compareTo(text.getEnd()) < 0; a = a.add(4)) {
            int x = mem.getInt(a);
            if ((x >>> 26) == 3) { long t = 0x80000000L | ((x & 0x3ffffffL) << 2); if (t >= lo && t < hi) seeds.add(t); }
        }
        // prologues
        for (int i = 2; i < n; i++)
            if ((w[i] >>> 16) == 0x27bd && (short) (w[i] & 0xffff) < 0 && (endsFunction(w, i) || (w[i - 2] >>> 26) == 2))
                seeds.add(BASE + 4L * i);

        int made = 0, dropped = 0;
        for (long s : seeds) {
            int i = (int) ((s - BASE) / 4);
            boolean prologue = (w[i] >>> 16) == 0x27bd && (short) (w[i] & 0xffff) < 0;
            if (!prologue && !endsFunction(w, i)) { dropped++; continue; }
            Address a = space.getAddress(s);
            if (getFunctionAt(a) != null) continue;
            new DisassembleCommand(a, null, true).applyTo(currentProgram, monitor);
            if (new CreateFunctionCmd(a).applyTo(currentProgram, monitor)) made++;
        }
        println("seeded " + made + " functions in " + module + " (" + dropped + " seeds dropped)");
        analyzeChanges(currentProgram);
        int count = 0;
        for (var f : currentProgram.getFunctionManager().getFunctions(new AddressSet(start, end.subtract(1)), true)) count++;
        println("after analysis: " + count + " functions in " + module);
    }

    // True if the word before index i closes a function: jr ra + delay slot, or zero padding.
    // (A prologue after j + delay slot is seeded too: a tail call ends the function before.)
    static boolean endsFunction(int[] w, int i) {
        if (i >= 2 && w[i - 2] == 0x03e00008) return true;
        if (i >= 1 && w[i - 1] == 0) return true;
        return false;
    }
}
