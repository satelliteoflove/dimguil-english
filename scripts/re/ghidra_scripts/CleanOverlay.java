// Post-analysis: remove junk functions from the overlay block.
//
// The main executable calls routines in several overlays at fixed addresses, and Ghidra
// follows every one of those calls into whichever overlay this program maps, so it
// disassembles data (or the middle of a function) as code. A function in the overlay is
// dropped when nothing that's kept in the overlay calls or jumps to it and either its
// entry doesn't look like a function start (no addiu sp,sp,-N prologue, and the word
// before isn't jr ra's delay slot or zero padding) or disassembly failed inside it or
// just past its end (an error bookmark: it ran into data). Repeats until nothing changes. Only the function
// records go; the instructions stay, since a junk entry can sit inside real code.
// Arg: module name (block OVL_<module>).
// @category Dimguil
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.listing.BookmarkType;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import java.util.*;

public class CleanOverlay extends GhidraScript {
    @Override
    public void run() throws Exception {
        MemoryBlock ovl = currentProgram.getMemory().getBlock("OVL_" + getScriptArgs()[0]);
        Memory mem = currentProgram.getMemory();
        FunctionManager fm = currentProgram.getFunctionManager();
        List<Address> errors = new ArrayList<>();
        Iterator<Bookmark> bi = currentProgram.getBookmarkManager().getBookmarksIterator(BookmarkType.ERROR);
        while (bi.hasNext()) { Address b = bi.next().getAddress(); if (ovl.contains(b)) errors.add(b); }
        Set<Function> drop = new HashSet<>();
        boolean changed = true;
        while (changed) {
            changed = false;
            for (Function f : fm.getFunctions(new AddressSet(ovl.getStart(), ovl.getEnd()), true)) {
                if (drop.contains(f) || f.getSymbol().getSource() == SourceType.USER_DEFINED) continue;   // ours
                if (looksLikeStart(mem, ovl, f.getEntryPoint()) && !broken(f, errors)) continue;
                boolean keptCaller = false;
                for (Reference r : getReferencesTo(f.getEntryPoint())) {
                    Address from = r.getFromAddress();
                    if (!ovl.contains(from)) continue;
                    Function g = fm.getFunctionContaining(from);
                    if (g == null || drop.contains(g) || g == f) continue;
                    // a branch or fall-through from the function that runs straight into this
                    // entry means the entry is the middle of that function, not a caller
                    boolean before = g.getBody().contains(f.getEntryPoint().subtract(4));
                    if (r.getReferenceType().isCall() || !before) { keptCaller = true; break; }
                }
                if (!keptCaller) { drop.add(f); changed = true; }
            }
        }
        for (Function f : drop) fm.removeFunction(f.getEntryPoint());
        // A junk entry in the middle of a real function cut that function's body short, and
        // removing the junk doesn't regrow it, so re-derive every body from its flow.
        int grown = 0;
        for (Function f : fm.getFunctions(new AddressSet(ovl.getStart(), ovl.getEnd()), true)) {
            long before = f.getBody().getNumAddresses();
            CreateFunctionCmd.fixupFunctionBody(currentProgram, f, monitor);
            if (f.getBody().getNumAddresses() > before) grown++;
        }
        println("dropped " + drop.size() + " junk functions from OVL_" + getScriptArgs()[0] + ", regrew " + grown);
    }

    static boolean broken(Function f, List<Address> errors) {
        Address lo = f.getBody().getMinAddress(), hi = f.getBody().getMaxAddress().add(8);
        for (Address b : errors) if (b.compareTo(lo) >= 0 && b.compareTo(hi) <= 0) return true;
        return false;
    }

    static boolean looksLikeStart(Memory mem, MemoryBlock ovl, Address a) {
        try {
            int x = mem.getInt(a);
            if ((x >>> 16) == 0x27bd && (short) (x & 0xffff) < 0) return true;
            if (a.subtract(ovl.getStart()) >= 8 && mem.getInt(a.subtract(8)) == 0x03e00008) return true;
            if (a.subtract(ovl.getStart()) >= 4 && mem.getInt(a.subtract(4)) == 0) return true;
        } catch (MemoryAccessException e) { }
        return false;
    }
}
