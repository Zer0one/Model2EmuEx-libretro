/* Recovered ElSemi 1.1a A68K CPU, used by the optional SCSP sound board build.
 * Native context starts at 00528ce4. See AUDIO_RE_ANALYSIS.md for evidence. */
#ifndef M2_A68K_H
#define M2_A68K_H
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t d[8], a[8];
    uint32_t ssp, sr_high, flags, x, pc, irq;
    /* Unrecovered slots, including original callback tokens, remain opaque.
     * These are never used as host pointers in the portable implementation. */
    uint32_t opaque22, ack_token, opaque24[4];
    uint32_t usp, vbr, fetch_bank, opaque31, raw_pc;
} a68k_registers;

typedef uint32_t (*a68k_read_fn)(void *, uint32_t);
/* Some native handlers consume EDX left by a bus read as their live flags.
 * Carry that observation separately from EAX; neither is a host pointer.
 * Board bindings must recover the original callback's EDX, not substitute
 * guest flags or assume a C calling convention preserves this register. */
typedef struct { uint32_t value, edx; } a68k_read_result;
typedef a68k_read_result (*a68k_read_observed_fn)(void *, uint32_t);
typedef void (*a68k_write_fn)(void *, uint32_t, uint32_t);
/* Next-handler scratch; control_flags is separate from guest/live EDX. */
typedef struct { uint32_t eax, control_flags; unsigned valid; } a68k_host_state;
typedef a68k_host_state (*a68k_write_observed_fn)(void *,uint32_t,uint32_t,uint32_t);
/* Live read callbacks expose EDX separately from guest flags, plus the host
 * control flags inherited by the next arithmetic/PUSHFD. Old value-only and
 * EAX/EDX observations do not establish control-flag provenance. */
typedef struct { a68k_read_result registers; uint32_t control_flags; unsigned valid; } a68k_read_observation;
typedef a68k_read_observation (*a68k_read_live_fn)(void *,uint32_t,uint32_t);
typedef struct {
    /* Direct data uses original word-swapped bytes. guest_base identifies
     * data[0], avoiding an invalid host pointer before the allocation. */
    uint8_t *data;
    uint32_t guest_base;
    size_t size;
    void *user;
    a68k_read_fn read[3];   /* byte, word, long; used only without data */
    a68k_write_fn write[3];
    a68k_read_observed_fn read_observed[3];
    a68k_write_observed_fn write_observed[3];
    a68k_read_live_fn read_live[3];
    uint32_t native_base; /* Original direct-map base token, not data's address. */
    unsigned native_base_valid;
} a68k_page;

enum { A68K_PAGE_COUNT = 4096 };
typedef enum { A68K_READ_SPACE, A68K_DATA_SPACE } a68k_read_space;
typedef enum { A68K_MAP_FETCH, A68K_MAP_DATA, A68K_MAP_WRITE } a68k_map_kind;
typedef enum {
    A68K_RETURN, A68K_FETCH, A68K_EXIT,
    /* Native branch at 00462c89, before recursive address-error dispatch.
     * The original tail bypasses pending CALL frames: an IRQ exit can RET to
     * saved ECX instead of the host caller. User-approved policy: latch a
     * fatal diagnostic here, without entering or repairing that host tail. */
    A68K_ODD_VECTOR,
    A68K_BINDING_ERROR, A68K_UNRECOVERED,
    /* Original signed host IDIV faults before its guest quotient check. */
    A68K_DIVS_HOST_OVERFLOW,
    /* RESET has already fetched its successor and jumps to that handler even
     * after exhausting cycles. The future execution loop must consume
     * prefetched_opcode directly, without another bus fetch or budget test. */
    A68K_PREFETCHED
} a68k_boundary;

typedef struct {
    a68k_boundary boundary; /* Zero means no fault. Not guest CPU state. */
    /* For DIVS host overflow: vector=0 (not a guest exception), exception_pc
     * is the instruction PC, target is the sign-extended divisor (-1). */
    uint32_t native_pc, vector, exception_pc, target, cycles, flags;
} a68k_fault;

typedef struct {
    a68k_registers r;
    /* Original ESI/EDX and 010ed9b0. Keep live and published values distinct. */
    uint32_t pc, flags, cycles;
    uint32_t illegal_opcode, illegal_pc; /* 010ed9b8 / 010ed9bc */
    uint32_t prefetched_opcode;
    unsigned prefetched_valid; /* Pending RESET successor across research pauses. */
    /* Research instruction-entry binding for original EAX high-byte consumers.
     * The future executor must propagate the original register/callback
     * results; no value is inferred from a portable host CPU register. */
    uint32_t entry_eax;
    unsigned entry_eax_valid;
    /* Virtual x86 frame provenance, scoped to the executing board/callback. */
    uint32_t dispatch_sp, write_wrapper_sp;
    a68k_fault fault;
    const a68k_page *read_pages, *data_pages, *write_pages, *fetch_page;
    const uint8_t *exception_cycles; /* Original 256-byte lookup, caller-owned. */
    uint32_t address_mask;
    void *user;
    a68k_read_fn vector_read;
    a68k_write_fn stack_word, stack_long;
    void (*bind)(void *, uint32_t);
    /* Live branch binding returns actual native EAX/control provenance and
     * updates fetch_page. It is never inferred from the C callback ABI. */
    a68k_host_state (*bind_observed)(void *,uint32_t,uint32_t);
    int32_t (*ack)(void *, unsigned);
    a68k_host_state (*ack_observed)(void *,unsigned,uint32_t);
    /* Bound host equivalent of the native optional RESET output callback.
     * Original pointer token is context+0x64 (opaque24[1]), never dereferenced. */
    void (*reset_output)(void *);
    a68k_host_state (*reset_observed)(void *,uint32_t);
} a68k_cpu;

/* Zero-initialize a new CPU before binding it. Fatal diagnostics are sticky:
 * every CPU entry rejects further execution, including native reset. Content
 * teardown/recreation, not a guest reset, owns recovery. The future sound-board
 * caller must surface the diagnostic and stop content; no frontend is wired yet.
 * Bindings must outlive calls. A binding error reports a missing/short host
 * mapping, not an invented guest bus value. No complete execute API exists. */
const char *a68k_fault_message(const a68k_cpu *cpu);
/* Native 004b3280/32c0/3310 range installers. Host storage remains bounded;
 * binding->data[0] corresponds to start. FETCH clears callback slots. */
int a68k_map_pages(a68k_page *pages,a68k_map_kind kind,uint32_t start,uint32_t end,const a68k_page *binding);
/* Returns the native EAX value, including retained high bits on narrow direct
 * reads. Callers must apply the original instruction's own width conversion. */
int a68k_read(const a68k_page *pages, a68k_read_space space, uint32_t address, unsigned width, uint32_t *value);
/* Requires explicit original EDX provenance. Missing observations fail before
 * performing a callback; the ordinary value-only API remains independent. */
int a68k_read_observed(const a68k_page *pages, a68k_read_space space, uint32_t address, unsigned width, a68k_read_result *result);
int a68k_read_live(const a68k_page *pages,a68k_read_space space,uint32_t address,unsigned width,a68k_read_result *result,a68k_host_state *host);
int a68k_write(const a68k_page *pages, uint32_t address, unsigned width, uint32_t value);
/* Observe original write-return EAX/control flags. Direct byte/word writes
 * leave the descriptor token in EAX; long writes leave the native base token.
 * Callback paths require explicit provenance and never call a void callback
 * as a fallback. This does not claim write-return EDX provenance. */
int a68k_write_observed(const a68k_page *pages,uint32_t address,unsigned width,uint32_t value,a68k_host_state *host);
int a68k_bind_pc(a68k_cpu *cpu, uint32_t pc);
a68k_host_state a68k_bind_pc_observed(a68k_cpu *cpu, uint32_t pc, uint32_t control);
a68k_boundary a68k_reset(a68k_cpu *cpu);
a68k_boundary a68k_exception_frame(a68k_cpu *cpu, unsigned vector);
/* Original exception body with explicit bus/binder scratch. Native odd-vector
 * diagnostics are retained; no recovery from the unsafe host tail is added. */
a68k_boundary a68k_exception_observed(a68k_cpu *cpu,unsigned vector,a68k_host_state *host);
a68k_boundary a68k_interrupt_entry(a68k_cpu *cpu);
a68k_boundary a68k_moveq(a68k_cpu *cpu, uint16_t opcode, uint32_t host_control_flags);
/* Native target tokens from the recovered table, never executable addresses.
 * Unknown targets remain explicit; they must not become generic ILLEGAL. */
a68k_boundary a68k_dispatch_target(a68k_cpu *cpu, uint32_t target, uint16_t opcode, uint32_t host_control_flags);
/* Live x86 scratch across instruction boundaries, represented as integers.
 * Control flags are distinct from guest/live EDX flags. Never initialize EAX
 * from the cycle budget by convention: original callers 004af01d, 004b3064
 * and 004cc736 arrive with different provenance (see PROVENANCE.md).
 * All original dispatch targets have observed paths. Their targeted checks
 * measure internal connection coverage, not every input/path, real board
 * callbacks, source identity or overall CPU completion.
 * Only the ordinary arithmetic/IF/DF host-flag domain is qualified. Other
 * control/trap/privileged flags remain explicit unrecovered inputs. Unknown
 * target tokens are rejected before mutation.
 * FETCH/PREFETCHED preserve a valid next-entry observation. Other boundaries
 * invalidate it; the native exit restores caller registers with POPAD. */
/* Native 00462b1c entry, including masked and accepted IRQ EAX=level.
 * Accepted IRQ requires explicit ack/read/write/binder observations. */
a68k_boundary a68k_begin_observed(a68k_cpu *cpu, a68k_host_state *host);
a68k_boundary a68k_step_observed(a68k_cpu *cpu, uint32_t target, uint16_t opcode, a68k_host_state *host);
/* Original RLE decoder; caller owns the immutable expanded token table.
 * No original EXE is required at runtime. Short/null storage is rejected
 * before writes. The target tokens are interpreted, never executed. */
enum { A68K_OPCODE_COUNT=65536 };
void a68k_init_exception_cycles(uint8_t costs[256]);
int a68k_init_dispatch(uint32_t *table,size_t capacity);
/* Continue LIVE state after begin_observed or a FETCH pause. Do not reload
 * published PC/flags between instructions. max_steps bounds research runs;
 * FETCH at that limit leaves live state and any RESET prefetch intact for
 * continuation. RESET consumes its prefetched opcode without a bus re-fetch
 * or budget check. Every other
 * boundary is returned explicitly (including an unqualified target).
 * steps counts handlers returning FETCH/EXIT or a native fault boundary,
 * not refused/unbound dispatch attempts. No complete sound CPU is implied. */
a68k_boundary a68k_run_live(a68k_cpu *cpu,const uint32_t *table,a68k_host_state *host,unsigned max_steps,unsigned *steps);
#endif
