// Write every function (entry, end, name, symbol source, block) to the file given as script arg.
// @category Dimguil
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import java.io.*;

public class DumpFunctions extends GhidraScript {
    @Override
    public void run() throws Exception {
        String out = getScriptArgs()[0];
        try (PrintWriter w = new PrintWriter(new FileWriter(out))) {
            w.println("entry,end,name,source,block");
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                var b = currentProgram.getMemory().getBlock(f.getEntryPoint());
                w.println(f.getEntryPoint() + "," + f.getBody().getMaxAddress() + "," + f.getName() + "," +
                          f.getSymbol().getSource() + "," + (b == null ? "" : b.getName()));
            }
        }
    }
}
