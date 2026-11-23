// Symbols ggml-quants.c and ggml-cpu/quants.c reference from the rest of ggml, which the
// harness does not link. Only the full-tensor quantize and validate entry points use the
// size helpers; the reference functions the harness calls never do, and those stubs abort
// if they are ever reached.
#include "ggml.h"
#include "ggml-impl.h"

#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

// fp16 -> fp32 table the generic CPU dot products read (simd-mappings.h:150), filled exactly
// as ggml_cpu_init does (ggml-cpu/ggml-cpu.c:3884): with ggml_compute_fp16_to_fp32.
float ggml_table_f32_f16[1 << 16];

void gm_init_tables(void) {
    for (int i = 0; i < (1 << 16); ++i) {
        union {
            uint16_t u16;
            ggml_fp16_t fp16;
        } u = {(uint16_t) i};
        ggml_table_f32_f16[i] = GGML_COMPUTE_FP16_TO_FP32(u.fp16);
    }
}

void ggml_abort(const char *file, int line, const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    fprintf(stderr, "ggml_abort at %s:%d: ", file, line);
    vfprintf(stderr, fmt, args);
    va_end(args);
    fputc('\n', stderr);
    abort();
}

static void unreachable(const char *what) {
    fprintf(stderr, "gm_harness: unexpected call to %s\n", what);
    abort();
}

size_t ggml_row_size(enum ggml_type type, int64_t ne) {
    (void) type;
    (void) ne;
    unreachable("ggml_row_size");
    return 0;
}

size_t ggml_type_size(enum ggml_type type) {
    (void) type;
    unreachable("ggml_type_size");
    return 0;
}

const char *ggml_type_name(enum ggml_type type) {
    (void) type;
    unreachable("ggml_type_name");
    return "";
}
