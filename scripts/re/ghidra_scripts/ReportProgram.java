// Print memory blocks, function counts and PsyQ info for the current program.
// @category Dimguil
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.framework.options.Options;

public class ReportProgram extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (MemoryBlock b : currentProgram.getMemory().getBlocks())
            println(String.format("block %-12s %s-%s init=%s overlay=%s", b.getName(), b.getStart(), b.getEnd(), b.isInitialized(), b.isOverlay()));
        int total = 0, named = 0;
        java.util.Map<String,Integer> src = new java.util.TreeMap<>();
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            total++;
            String s = f.getSymbol().getSource().toString();
            src.merge(s, 1, Integer::sum);
            if (!f.getName().startsWith("FUN_")) named++;
        }
        println("functions " + total + " named " + named + " by source " + src);
        Options o = currentProgram.getOptions(Program.PROGRAM_INFO);
        for (String n : o.getOptionNames()) if (n.toLowerCase().contains("psyq") || n.toLowerCase().contains("version")) println("option " + n + " = " + o.getValueAsString(n));
        java.util.Map<String,StringBuilder> ex = new java.util.TreeMap<>();
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            String s = f.getSymbol().getSource().toString();
            StringBuilder sb = ex.computeIfAbsent(s, x -> new StringBuilder());
            if (sb.length() < 600) sb.append(f.getName()).append("@").append(f.getEntryPoint()).append(" ");
        }
        for (String s : ex.keySet()) println("sample " + s + ": " + ex.get(s));
    }
}
