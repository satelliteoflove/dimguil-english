// Post-analysis: write the functions the PSX loader labelled from PsyQ signatures (any
// non-default name before our symbols are applied, in the executable from the end of the
// game code up to the overlay window) to the CSV given as the first arg. ExportModule
// treats these as library code and doesn't decompile them. The loader also names main()
// (game code) and Ghidra names some switch fragments (caseD_0), so the range matters.
// Args: CSV path, game-code end (hex).
// @category Dimguil
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.SourceType;
import java.io.*;

public class RecordLibrary extends GhidraScript {
    @Override
    public void run() throws Exception {
        long gameEnd = Long.decode(getScriptArgs()[1]);
        try (PrintWriter w = new PrintWriter(new FileWriter(getScriptArgs()[0]))) {
            w.println("address,name");
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                long a = f.getEntryPoint().getOffset();
                if (f.getSymbol().getSource() != SourceType.DEFAULT && a >= gameEnd && a < 0x800a1000L)
                    w.println(f.getEntryPoint() + "," + f.getName());
            }
        }
    }
}
