// Apply names, comments and types from a TSV made by scripts/re/ghidra.py (address, name,
// kind, comment, type). kind: function (creates the function if missing), label (a code
// location inside a function), global or table (a data label). Our names replace the PsyQ
// labels only where the TSV names the same address. type is a C type from types.h or a
// built-in (u8, u16, u32, s8, s16, s32, char), optionally with [N] for an array; it's
// applied to global and table rows. Args: TSV path, types.h path.
// @category Dimguil
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.util.cparser.C.CParser;
import ghidra.program.model.address.*;
import ghidra.program.model.data.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.util.CodeUnitInsertionException;
import java.nio.file.*;

public class ApplySymbols extends GhidraScript {
    @Override
    public void run() throws Exception {
        DataTypeManager dtm = currentProgram.getDataTypeManager();
        if (getScriptArgs().length > 1) {
            CParser parser = new CParser(dtm, true, null);
            parser.parse(Files.readString(Paths.get(getScriptArgs()[1])));
        }
        int n = 0, bad = 0, typed = 0;
        SymbolTable st = currentProgram.getSymbolTable();
        Listing listing = currentProgram.getListing();
        AddressSpace space = currentProgram.getAddressFactory().getDefaultAddressSpace();
        for (String line : Files.readAllLines(Paths.get(getScriptArgs()[0]))) {
            if (line.isBlank()) continue;
            String[] f = line.split("\t", -1);
            Address a = space.getAddress(Long.parseLong(f[0], 16));
            String name = f[1], kind = f[2], comment = f[3].replace("\\n", "\n");
            String type = f.length > 4 ? f[4].trim() : "";
            if (!currentProgram.getMemory().contains(a)) continue;
            try {
                if (kind.equals("function")) {
                    Function fn = getFunctionAt(a);
                    if (fn == null && currentProgram.getMemory().getBlock(a).isInitialized()) {
                        new DisassembleCommand(a, null, true).applyTo(currentProgram, monitor);
                        Function inside = getFunctionContaining(a);
                        if (inside == null) new CreateFunctionCmd(a).applyTo(currentProgram, monitor);
                        fn = getFunctionAt(a);
                    }
                    if (fn != null) {
                        fn.setName(name, SourceType.USER_DEFINED);
                        fn.setComment(comment.isEmpty() ? null : comment);
                    } else {
                        st.createLabel(a, name, SourceType.USER_DEFINED).setPrimary();
                        if (!comment.isEmpty()) listing.setComment(a, CodeUnit.PRE_COMMENT, comment);
                    }
                } else {
                    Symbol s = st.createLabel(a, name, SourceType.USER_DEFINED);
                    s.setPrimary();
                    if (!comment.isEmpty())
                        listing.setComment(a, kind.equals("label") ? CodeUnit.PRE_COMMENT : CodeUnit.PLATE_COMMENT, comment);
                    if (!type.isEmpty() && !kind.equals("label")) {
                        DataType dt = resolve(dtm, type);
                        if (dt == null) { println("unknown type " + type + " for " + name); bad++; }
                        else { DataUtilities.createData(currentProgram, a, dt, -1, DataUtilities.ClearDataMode.CLEAR_ALL_CONFLICT_DATA); typed++; }
                    }
                }
                n++;
            } catch (Exception e) {
                println("could not apply " + f[0] + " " + name + ": " + e.getMessage());
                bad++;
            }
        }
        println("applied " + n + " symbols, " + typed + " typed (" + bad + " failed)");
    }

    static DataType resolve(DataTypeManager dtm, String type) {
        int count = 0;
        String base = type;
        if (type.endsWith("]")) {
            base = type.substring(0, type.indexOf('[')).trim();
            count = Integer.decode(type.substring(type.indexOf('[') + 1, type.length() - 1).trim());
        }
        DataType dt = null;
        java.util.List<DataType> found = new java.util.ArrayList<>();
        dtm.findDataTypes(base, found);
        if (!found.isEmpty()) dt = found.get(0);
        if (dt == null) switch (base) {
            case "u8": dt = ByteDataType.dataType; break;
            case "s8": case "char": dt = SignedByteDataType.dataType; break;
            case "u16": dt = UnsignedShortDataType.dataType; break;
            case "s16": dt = ShortDataType.dataType; break;
            case "u32": dt = UnsignedIntegerDataType.dataType; break;
            case "s32": dt = IntegerDataType.dataType; break;
        }
        if (dt == null) return null;
        return count > 0 ? new ArrayDataType(dt, count, dt.getLength()) : dt;
    }
}
