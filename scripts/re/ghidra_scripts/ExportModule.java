// Export one module: decompiled C for each of its game functions, plus an index of calls
// and the globals each function reads and writes.
// Args: output dir, module name, library CSV (functions to skip), main game-code end (hex).
//   module MAIN exports the executable's .text below that end address;
//   any other module exports the functions in block OVL_<module>.
// Writes <out>/<addr>_<name>.c and <out>/index.json (see scripts/re/README.md).
// @category Dimguil
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public class ExportModule extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        Path out = Paths.get(a[0]);
        String module = a[1];
        Set<String> library = new HashSet<>();
        for (String line : Files.readAllLines(Paths.get(a[2]))) library.add(line.split(",")[0]);
        long mainEnd = Long.parseLong(a[3].replace("0x", ""), 16);
        Files.createDirectories(out);
        try (DirectoryStream<Path> old = Files.newDirectoryStream(out, "*.c")) { for (Path p : old) Files.delete(p); }

        Memory mem = currentProgram.getMemory();
        AddressSetView range;
        if (module.equals("MAIN")) {
            MemoryBlock text = mem.getBlock(".text");
            range = new AddressSet(text.getStart(), text.getStart().getNewAddress(mainEnd - 1));
        } else {
            MemoryBlock ovl = mem.getBlock("OVL_" + module);
            range = new AddressSet(ovl.getStart(), ovl.getEnd());
        }

        DecompInterface dec = new DecompInterface();
        DecompileOptions opts = new DecompileOptions();
        opts.grabFromProgram(currentProgram);
        dec.setOptions(opts);
        dec.toggleCCode(true);
        dec.toggleSyntaxTree(true);
        dec.setSimplificationStyle("decompile");
        dec.openProgram(currentProgram);

        FunctionManager fm = currentProgram.getFunctionManager();
        ReferenceManager rm = currentProgram.getReferenceManager();
        // Raw pointer words: Ghidra makes no reference from an undefined word in a table, so
        // scan the module's own bytes (and the executable's data) for words equal to a
        // function entry, outside any function body. Handler tables show up this way.
        Map<Long, List<String>> rawPtrs = new HashMap<>();
        List<MemoryBlock> scan = new ArrayList<>();
        for (MemoryBlock b : mem.getBlocks())
            if (b.isInitialized() && (b.getName().startsWith("OVL_") || b.getName().equals(".data")
                    || b.getName().equals(".rdata") || b.getName().equals(".sdata"))) scan.add(b);
        for (MemoryBlock b : scan) {
            for (Address p = b.getStart(); p.compareTo(b.getEnd().subtract(3)) <= 0; p = p.add(4)) {
                long v = mem.getInt(p) & 0xffffffffL;
                if (v < 0x80010000L || v >= 0x80200000L || (v & 3) != 0) continue;
                if (fm.getFunctionContaining(p) != null) continue;
                Function t = fm.getFunctionAt(p.getNewAddress(v));
                if (t != null) rawPtrs.computeIfAbsent(v, k -> new ArrayList<>()).add("data:" + p);
            }
        }
        StringBuilder idx = new StringBuilder("{\"module\": \"" + module + "\", \"functions\": [\n");
        boolean first = true;
        int count = 0, failed = 0;
        for (Function f : fm.getFunctions(range, true)) {
            String ep = f.getEntryPoint().toString();
            if (library.contains(ep)) continue;
            TreeSet<String> callers = new TreeSet<>(), callees = new TreeSet<>();
            TreeSet<String> reads = new TreeSet<>(), writes = new TreeSet<>(), addrs = new TreeSet<>();
            for (Reference r : rm.getReferencesTo(f.getEntryPoint())) {
                Function g = fm.getFunctionContaining(r.getFromAddress());
                if (g != null && r.getReferenceType().isFlow()) callers.add(g.getEntryPoint().toString());
                else if (g != null) addrs.add(g.getEntryPoint().toString());   // pointer taken in code
                else addrs.add("data:" + r.getFromAddress());                    // in a table or struct
            }
            addrs.addAll(rawPtrs.getOrDefault(f.getEntryPoint().getOffset(), List.of()));
            for (Function g : f.getCalledFunctions(monitor)) callees.add(g.getEntryPoint().toString());
            AddressIterator it = rm.getReferenceSourceIterator(f.getBody(), true);
            while (it.hasNext()) {
                for (Reference r : rm.getReferencesFrom(it.next())) {
                    if (!r.getToAddress().isMemoryAddress() || r.isStackReference()) continue;
                    RefType t = r.getReferenceType();
                    if (t.isFlow()) continue;
                    String to = r.getToAddress().toString();
                    if (t.isWrite()) writes.add(to);
                    if (t.isRead()) reads.add(to);
                    if (!t.isRead() && !t.isWrite()) reads.add(to);   // address taken (lui/addiu pair)
                }
            }
            String name = f.getName();
            String c;
            DecompileResults res = dec.decompileFunction(f, 120, monitor);
            if (res != null && res.decompileCompleted()) c = res.getDecompiledFunction().getC();
            else { c = "/* decompile failed: " + (res == null ? "null" : res.getErrorMessage()) + " */\n"; failed++; }
            boolean suspect = c.contains("halt_baddata");
            String plate = f.getComment() == null ? "" : f.getComment();
            String head = "// " + module + " " + ep + " " + name + "  (" + f.getBody().getNumAddresses() + " bytes)\n"
                        + "// callers: " + String.join(" ", callers) + "\n"
                        + (addrs.isEmpty() ? "" : "// address taken by: " + String.join(" ", addrs) + "\n")
                        + (suspect ? "// SUSPECT: decompiles into bad data; probably not a function in this module (a call\n"
                                   + "// from the executable meant for another overlay)\n" : "")
                        + (plate.isEmpty() ? "" : "// " + plate.replace("\n", "\n// ") + "\n");
            Files.writeString(out.resolve(ep + "_" + name + ".c"), head + c);
            idx.append(first ? "" : ",\n").append("{\"addr\": \"").append(ep)
               .append("\", \"name\": \"").append(name.replace("\"", "'"))
               .append("\", \"end\": \"").append(f.getBody().getMaxAddress())
               .append("\", \"size\": ").append(f.getBody().getNumAddresses())
               .append(", \"callers\": ").append(jarr(callers))
               .append(", \"pointer_from\": ").append(jarr(addrs))
               .append(", \"callees\": ").append(jarr(callees))
               .append(", \"reads\": ").append(jarr(reads))
               .append(", \"writes\": ").append(jarr(writes))
               .append(suspect ? ", \"suspect\": true" : "").append("}");
            first = false;
            count++;
        }
        idx.append("\n]}\n");
        Files.writeString(out.resolve("index.json"), idx.toString());
        dec.dispose();
        println("exported " + count + " functions of " + module + " (" + failed + " failed to decompile)");
    }

    static String jarr(Collection<String> s) {
        StringBuilder b = new StringBuilder("[");
        boolean first = true;
        for (String x : s) { b.append(first ? "" : ", ").append('"').append(x).append('"'); first = false; }
        return b.append(']').toString();
    }
}
