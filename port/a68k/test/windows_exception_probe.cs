// ROM-free debugger probe of the original process and its real SEH chain.
// Run in 32-bit Windows PowerShell. Only the child created here is controlled.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;

public static class A68kWindowsExceptionProbe {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct Startup {
        public uint cb; public string reserved, desktop, title;
        public uint x,y,xsize,ysize,xchars,ychars,fill,flags;
        public ushort show,reserved2; public IntPtr data,input,output,error;
    }
    [StructLayout(LayoutKind.Sequential)]
    struct ProcessInfo { public IntPtr process,thread; public uint pid,tid; }
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern bool CreateProcess(string app,string command,IntPtr pa,IntPtr ta,
        bool inherit,uint flags,IntPtr environment,string cwd,ref Startup startup,out ProcessInfo process);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool WaitForDebugEvent(byte[] data,uint milliseconds);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool ContinueDebugEvent(uint pid,uint tid,uint status);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool ReadProcessMemory(IntPtr p,IntPtr address,byte[] data,uint size,out uint count);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool WriteProcessMemory(IntPtr p,IntPtr address,byte[] data,uint size,out uint count);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool FlushInstructionCache(IntPtr p,IntPtr address,uint size);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool GetThreadContext(IntPtr thread,byte[] context);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool SetThreadContext(IntPtr thread,byte[] context);
    [DllImport("kernel32.dll")] static extern bool TerminateProcess(IntPtr p,uint status);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr handle,uint milliseconds);
    public sealed class Row {
        public string kind,code,address;
        public uint firstChance,pid,tid;
        public string[] context;
    }
    static uint U(byte[] b,int offset) { return BitConverter.ToUInt32(b,offset); }
    static string Hex(uint x) { return x.ToString("x8"); }
    static void Put(byte[] b,int offset,uint x) { Array.Copy(BitConverter.GetBytes(x),0,b,offset,4); }
    static void Check(bool ok,string what) {
        if(!ok)throw new Win32Exception(Marshal.GetLastWin32Error(),what);
    }
    static byte[] Read(IntPtr p,uint address,uint size) {
        byte[] data=new byte[size];uint count;
        Check(ReadProcessMemory(p,new IntPtr(address),data,size,out count)&&count==size,"ReadProcessMemory");
        return data;
    }
    static void Write(IntPtr p,uint address,byte[] data) {
        uint count;
        Check(WriteProcessMemory(p,new IntPtr(address),data,(uint)data.Length,out count)&&count==data.Length,"WriteProcessMemory");
        Check(FlushInstructionCache(p,new IntPtr(address),(uint)data.Length),"FlushInstructionCache");
    }
    static string[] Snapshot(IntPtr p) {
        byte[] b=Read(p,0x528ce4,132);string[] words=new string[33];
        for(int i=0;i<33;i++)words[i]=Hex(U(b,i*4));return words;
    }
    public static List<Row> Run(string exe,string cwd,uint dividend) {
        if(IntPtr.Size!=4)throw new Exception("Use 32-bit PowerShell for the x86 debugger ABI");
        const uint gate=0x4f6900,tail=0x4819e0;
        Startup si=new Startup();si.cb=(uint)Marshal.SizeOf(si);ProcessInfo pi;
        Check(CreateProcess(exe,"\""+exe+"\"",IntPtr.Zero,IntPtr.Zero,false,2,
            IntPtr.Zero,cwd,ref si,out pi),"CreateProcess DEBUG_ONLY_THIS_PROCESS");
        List<Row> rows=new List<Row>();bool exited=false,injected=false,initialBreakpoint=false;
        Stopwatch timer=Stopwatch.StartNew();byte gateByte=0,tailByte=0;
        try {
            while(timer.ElapsedMilliseconds<30000) {
                byte[] ev=new byte[96];
                if(!WaitForDebugEvent(ev,1000)) {
                    if(Marshal.GetLastWin32Error()==121)continue;
                    Check(false,"WaitForDebugEvent");
                }
                uint type=U(ev,0),pid=U(ev,4),tid=U(ev,8),status=0x10002;
                if(type==3) {
                    if(U(ev,24)!=0x400000)throw new Exception("Unexpected original image base");
                    gateByte=Read(pi.process,gate,1)[0];tailByte=Read(pi.process,tail,1)[0];
                    if(gateByte!=0x8b||tailByte!=0x0f)throw new Exception("Unexpected breakpoint bytes");
                    Write(pi.process,gate,new byte[]{0xcc});Write(pi.process,tail,new byte[]{0xcc});
                    if(U(ev,12)!=0)CloseHandle(new IntPtr(U(ev,12)));
                } else if(type==6) {
                    if(U(ev,12)!=0)CloseHandle(new IntPtr(U(ev,12)));
                } else if(type==1) {
                    uint code=U(ev,12),address=U(ev,24),first=U(ev,92);
                    rows.Add(new Row {kind="exception",code=Hex(code),address=Hex(address),
                        firstChance=first,pid=pid,tid=tid});
                    if(code==0x80000003&&address==gate&&!injected) {
                        if(tid!=pi.tid)throw new Exception("Main-loop breakpoint on unexpected thread");
                        Write(pi.process,gate,new byte[]{gateByte});
                        Write(pi.process,0x528ce4,BitConverter.GetBytes((uint)0xffff));
                        Write(pi.process,0x528ce8,BitConverter.GetBytes(dividend));
                        Write(pi.process,0x10ed9b0,BitConverter.GetBytes((uint)200));
                        byte[] c=new byte[716];Put(c,0,0x10007);
                        Check(GetThreadContext(pi.thread,c),"GetThreadContext");
                        // Existing main-loop SEH frame and host stack remain
                        // untouched. Enter the unchanged DIVS D0,D1 body.
                        Put(c,184,0x481950);Put(c,172,0x83c0);Put(c,160,0x1000);Put(c,168,0x202);
                        Check(SetThreadContext(pi.thread,c),"SetThreadContext");injected=true;
                        rows.Add(new Row {kind="injected",address=Hex(0x481950),code=Hex(dividend)});
                    } else if(code==0x80000003&&address==tail&&injected) {
                        rows.Add(new Row {kind="guest-overflow-tail",context=Snapshot(pi.process)});
                        // Control case ends before its synthetic next fetch.
                        Check(TerminateProcess(pi.process,0),"Terminate owned control process");
                    } else if(code==0x80000003&&!initialBreakpoint&&!injected) {
                        initialBreakpoint=true;
                    } else {
                        if(injected&&address==0x48198c)
                            rows.Add(new Row {kind="idiv-state",context=Snapshot(pi.process),firstChance=first});
                        // Never claim that a debugger-handled exception was
                        // recovered by ElSemi: pass both chances to Windows.
                        status=0x80010001;
                    }
                } else if(type==5) {
                    rows.Add(new Row {kind="process-exit",code=Hex(U(ev,12)),pid=pid});exited=true;
                }
                Check(ContinueDebugEvent(pid,tid,status),"ContinueDebugEvent");
                if(exited)break;
            }
            if(!exited)rows.Add(new Row {kind="probe-timeout"});
            if(!injected)rows.Add(new Row {kind="probe-not-injected"});
            return rows;
        } finally {
            if(!exited)TerminateProcess(pi.process,0xdead);
            WaitForSingleObject(pi.process,3000);CloseHandle(pi.thread);CloseHandle(pi.process);
        }
    }

    // NBCD imports PUSHFD after DAS, unlike ABCD/SBCD's explicit flag merge.
    // Measure all byte/X pairs in one original process with its existing SEH.
    public static List<Row> RunNbcd(string exe,string cwd) {
        if(IntPtr.Size!=4)throw new Exception("Use 32-bit PowerShell");
        const uint gate=0x4f6900,tail=0x4866b9;
        Startup si=new Startup();si.cb=(uint)Marshal.SizeOf(si);ProcessInfo pi;
        Check(CreateProcess(exe,"\""+exe+"\"",IntPtr.Zero,IntPtr.Zero,false,2,
            IntPtr.Zero,cwd,ref si,out pi),"CreateProcess NBCD");
        List<Row> rows=new List<Row>();bool exited=false,injected=false,loader=false;
        int index=0;Stopwatch timer=Stopwatch.StartNew();byte gateByte=0;
        try {
            while(timer.ElapsedMilliseconds<90000) {
                byte[] ev=new byte[96];
                if(!WaitForDebugEvent(ev,1000)) {
                    if(Marshal.GetLastWin32Error()==121)continue;
                    Check(false,"WaitForDebugEvent NBCD");
                }
                uint type=U(ev,0),pid=U(ev,4),tid=U(ev,8),status=0x10002;
                bool next=false;
                if(type==3) {
                    if(U(ev,24)!=0x400000)throw new Exception("Unexpected image base");
                    gateByte=Read(pi.process,gate,1)[0];
                    if(gateByte!=0x8b||Read(pi.process,tail,1)[0]!=0x0f)
                        throw new Exception("Unexpected NBCD breakpoint bytes");
                    Write(pi.process,gate,new byte[]{0xcc});Write(pi.process,tail,new byte[]{0xcc});
                    if(U(ev,12)!=0)CloseHandle(new IntPtr(U(ev,12)));
                } else if(type==6) {
                    if(U(ev,12)!=0)CloseHandle(new IntPtr(U(ev,12)));
                } else if(type==1) {
                    uint code=U(ev,12),address=U(ev,24);
                    if(code==0x80000003&&address==gate&&!injected) {
                        if(tid!=pi.tid)throw new Exception("Unexpected NBCD thread");
                        Write(pi.process,gate,new byte[]{gateByte});injected=true;next=true;
                    } else if(code==0x80000003&&address==tail&&injected) {
                        string[] snapshot=Snapshot(pi.process);
                        rows.Add(new Row {kind="nbcd",code=Hex((uint)index),
                            context=new string[]{Hex((uint)index>>1),Hex((uint)index&1),snapshot[0],snapshot[19]}});
                        ++index;
                        if(index==512)Check(TerminateProcess(pi.process,0),"Terminate owned NBCD process");
                        else next=true;
                    } else if(code==0x80000003&&!loader&&!injected) {loader=true;}
                    else {
                        rows.Add(new Row {kind="exception",code=Hex(code),address=Hex(address),firstChance=U(ev,92)});
                        status=0x80010001;
                    }
                } else if(type==5) {
                    rows.Add(new Row {kind="process-exit",code=Hex(U(ev,12))});exited=true;
                }
                if(next) {
                    Write(pi.process,0x528ce4,BitConverter.GetBytes(0x12340000u|((uint)index>>1)));
                    Write(pi.process,0x528d30,BitConverter.GetBytes(0xfeed0000u|((uint)index&1)));
                    Write(pi.process,0x10ed9b0,BitConverter.GetBytes((uint)200));
                    byte[] c=new byte[716];Put(c,0,0x10007);
                    Check(GetThreadContext(pi.thread,c),"GetThreadContext NBCD");
                    Put(c,184,0x486680);Put(c,172,0x4800);Put(c,160,0x1000);Put(c,168,0xa83);Put(c,192,0x202);
                    Check(SetThreadContext(pi.thread,c),"SetThreadContext NBCD");
                }
                Check(ContinueDebugEvent(pid,tid,status),"ContinueDebugEvent NBCD");
                if(exited)break;
            }
            if(!exited||index!=512)rows.Add(new Row {kind="probe-incomplete",code=Hex((uint)index)});
            return rows;
        } finally {
            if(!exited)TerminateProcess(pi.process,0xdead);
            WaitForSingleObject(pi.process,3000);CloseHandle(pi.thread);CloseHandle(pi.process);
        }
    }
}
