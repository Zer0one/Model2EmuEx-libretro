// ROM-free original-code oracle. Maps the pinned original PE without running
// its application entry point or resolving imports. Only the selected M2C
// numerical body and its original CRT conversion execute. Requires x86 CLR;
// Windows on ARM executes it through the OS's x86 translator, not physical x86.
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;

class OriginalFp {
    const int Arena = 0x30000000;
    const string Expected = "2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc";
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern IntPtr VirtualAlloc(IntPtr address, UIntPtr bytes, uint allocation, uint protection);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate void Execute(IntPtr input, IntPtr output);
    static uint U32(byte[] b, int off) { return BitConverter.ToUInt32(b, off); }
    static void Word(int address, uint value) { Marshal.WriteInt32(new IntPtr(address), unchecked((int)value)); }
    static void Allocate(int address, uint bytes) {
        if (VirtualAlloc(new IntPtr(address), new UIntPtr(bytes), 0x3000, 0x40) != new IntPtr(address))
            throw new Exception("VirtualAlloc " + address.ToString("x") + ": " + Marshal.GetLastWin32Error());
    }
    static int Main(string[] args) {
        if (args.Length != 4 || IntPtr.Size != 4) { Console.Error.WriteLine("x86 oracle: EXE trampoline input output"); return 2; }
        try {
            byte[] exe = File.ReadAllBytes(args[0]);
            using (SHA256 sha = SHA256.Create()) {
                string hash = BitConverter.ToString(sha.ComputeHash(exe)).Replace("-", "").ToLowerInvariant();
                if (hash != Expected) throw new Exception("Original EXE hash mismatch");
            }
            int pe = (int)U32(exe, 0x3c), optional = pe + 24;
            if (U32(exe, optional + 28) != 0x400000) throw new Exception("Original image base mismatch");
            // Map only original code/constants/globals used by these bodies.
            // Reserving the entire PE can overlap unrelated CLR allocations.
            int[] pages = {0x4b0000, 0x500000, 0x510000};
            int sections = BitConverter.ToUInt16(exe, pe + 6), table = optional + BitConverter.ToUInt16(exe, pe + 20);
            foreach (int page in pages) {
                Allocate(page, 0x10000);
                for (int n = 0; n < sections; ++n) {
                    int s = table + n * 40, va = 0x400000 + (int)U32(exe, s + 12);
                    int begin = Math.Max(page, va), end = Math.Min(page + 0x10000, va + (int)U32(exe, s + 16));
                    if (end > begin) Marshal.Copy(exe, (int)U32(exe, s + 20) + begin - va, new IntPtr(begin), end - begin);
                }
            }
            // CLR can occupy the original global pages. Relocate ONLY the
            // two active-state/record pointers and CRT SSE2 flag operands.
            // The verified manifest contains LLVM-decoded absolute operands;
            // no opcode, branch, FP instruction or constant changes.
            Allocate(0x31000000, 0x20000);
            using (BinaryReader reloc = new BinaryReader(File.OpenRead(Path.ChangeExtension(args[1], ".reloc")))) {
                while (reloc.BaseStream.Position < reloc.BaseStream.Length) {
                    uint at = reloc.ReadUInt32(), old = reloc.ReadUInt32(), value = reloc.ReadUInt32();
                    if (!(at >= 0x4b0000 && at < 0x4c0000 || at >= 0x500000 && at < 0x510000)) throw new Exception("Relocation target range");
                    uint mapped = old == 0x10481f4 ? 0x310081f4u : old == 0x104824c ? 0x3100824cu : old == 0x10f1fec ? 0x31011fecu : 0u;
                    if (value != mapped || mapped == 0 || unchecked((uint)Marshal.ReadInt32(new IntPtr(at))) != old) throw new Exception("Relocation mismatch");
                    Word((int)at, value);
                }
            }
            Allocate(Arena, 0x2000);
            Word(0x310081f4, Arena + 0x200); Word(0x3100824c, Arena);
            Word(Arena, Arena + 0x1240); Word(Arena + 0x14, Arena + 0x1240);
            Word(Arena + 4, Arena + 0x1250); Word(Arena + 0x18, Arena + 0x1250);
            // MOV EAX,[absolute operand]; RET. The operand readers alone are fixtures.
            Marshal.Copy(new byte[] {0xa1,0,0x12,0,0x30,0xc3}, 0, new IntPtr(Arena + 0x1240), 6);
            Marshal.Copy(new byte[] {0xa1,4,0x12,0,0x30,0xc3}, 0, new IntPtr(Arena + 0x1250), 6);
            Word(Arena + 0x1300, 0x1f80);
            byte[] trampoline = File.ReadAllBytes(args[1]);
            if (trampoline.Length > 0x200) throw new Exception("Oversized trampoline");
            Marshal.Copy(trampoline, 0, new IntPtr(Arena + 0x1400), trampoline.Length);
            Execute run = (Execute)Marshal.GetDelegateForFunctionPointer(new IntPtr(Arena + 0x1400), typeof(Execute));
            int count = 0;
            using (BinaryReader input = new BinaryReader(File.OpenRead(args[2])))
            using (BinaryWriter output = new BinaryWriter(File.Create(args[3]))) {
                while (input.BaseStream.Position < input.BaseStream.Length) {
                    uint[] words = new uint[7];
                    for (int i = 0; i < 7; ++i) { words[i] = input.ReadUInt32(); Word(Arena + 0x1600 + i * 4, words[i]); }
                    if (words[0] < 0x4b3fb0 || words[0] > 0x4b6690) throw new Exception("Entry outside FP range");
                    Word(Arena + 0x161c, words[4]); Word(Arena + 0x1620, words[5]); Word(Arena + 0x1624, 0xffff);
                    run(new IntPtr(Arena + 0x1600), new IntPtr(Arena + 0x1680));
                    for (int i = 0; i < 4; ++i) output.Write(unchecked((uint)Marshal.ReadInt32(new IntPtr(Arena + 0x1680 + i * 4))));
                    ++count;
                }
            }
            Console.WriteLine("Original x86 M2C numerical executions: " + count);
            return 0;
        } catch (Exception e) { Console.Error.WriteLine(e); return 1; }
    }
}
