// C harness for the golden model: runs llama.cpp's own reference functions (f46bc30,
// generic CPU path) on raw inputs so the Python model can be compared bit for bit.
//
//   gm_harness deq <q4_K|q5_K|q6_K|q8_0> IN OUT   raw blocks -> binary32 values
//   gm_harness quant <q8_K|q8_0> IN OUT           binary32 values -> raw blocks
//   gm_harness dot <q4_K|q5_K|q6_K|q8_0> W Y OUT  each weight row . activation row -> binary32
//
// Built by build.sh with -DGGML_CPU_GENERIC -ffp-contract=off (SEMANTICS.md section 1).
#define GGML_COMMON_DECL_C
#include "ggml-common.h"
#include "ggml-quants.h"
#include "quants.h"  // ggml-cpu: the vec_dot entry points (the generic ones under GGML_CPU_GENERIC)

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *read_all(const char *path, size_t *size) {
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    void *buf = malloc(n > 0 ? (size_t) n : 1);
    if (n > 0 && fread(buf, 1, (size_t) n, f) != (size_t) n) { perror(path); exit(2); }
    fclose(f);
    *size = (size_t) n;
    return buf;
}

static void write_all(const char *path, const void *buf, size_t size) {
    FILE *f = fopen(path, "wb");
    if (!f || fwrite(buf, 1, size, f) != size) { perror(path); exit(2); }
    fclose(f);
}

static int deq(const char *type, const char *in, const char *out) {
    size_t size;
    void *x = read_all(in, &size);
    size_t bsize, per;
    if (!strcmp(type, "q4_K")) { bsize = sizeof(block_q4_K); per = QK_K; }
    else if (!strcmp(type, "q5_K")) { bsize = sizeof(block_q5_K); per = QK_K; }
    else if (!strcmp(type, "q6_K")) { bsize = sizeof(block_q6_K); per = QK_K; }
    else if (!strcmp(type, "q8_0")) { bsize = sizeof(block_q8_0); per = QK8_0; }
    else { fprintf(stderr, "unknown type %s\n", type); return 2; }
    if (size % bsize) { fprintf(stderr, "%zu bytes is not whole %s blocks\n", size, type); return 2; }
    int64_t k = (int64_t) (size / bsize * per);
    float *y = malloc((size_t) k * sizeof(float) + 1);
    if (!strcmp(type, "q4_K")) dequantize_row_q4_K(x, y, k);
    else if (!strcmp(type, "q5_K")) dequantize_row_q5_K(x, y, k);
    else if (!strcmp(type, "q6_K")) dequantize_row_q6_K(x, y, k);
    else dequantize_row_q8_0(x, y, k);
    write_all(out, y, (size_t) k * sizeof(float));
    return 0;
}

// Activation quantization: raw binary32 values -> raw blocks. The output is pre-filled with
// 0xA5 so a caller can see bytes the reference leaves unwritten (q8_K bsums of an all-zero
// block).
static int quant(const char *type, const char *in, const char *out) {
    size_t size;
    float *x = read_all(in, &size);
    int64_t k = (int64_t) (size / sizeof(float));
    size_t bsize, per;
    if (!strcmp(type, "q8_K")) { bsize = sizeof(block_q8_K); per = QK_K; }
    else if (!strcmp(type, "q8_0")) { bsize = sizeof(block_q8_0); per = QK8_0; }
    else { fprintf(stderr, "unknown type %s\n", type); return 2; }
    if (size % sizeof(float) || k % (int64_t) per) { fprintf(stderr, "not whole %s blocks\n", type); return 2; }
    size_t n = (size_t) k / per * bsize;
    void *y = malloc(n + 1);
    memset(y, 0xA5, n);
    if (!strcmp(type, "q8_K")) quantize_row_q8_K_ref(x, y, k);
    else quantize_row_q8_0_ref(x, y, k);
    write_all(out, y, n);
    return 0;
}

// Dot products: every row of W (raw weight blocks) against the one activation row Y (raw
// q8_K or q8_0 blocks) -> one binary32 per row. One row per call (nrc = 1), as the generic
// mul_mat path does (ggml-cpu/ggml-cpu.c:1165).
typedef void (*vec_dot_fn)(int, float *, size_t, const void *, size_t, const void *, size_t, int);

static int dot(const char *type, const char *win, const char *yin, const char *out) {
    size_t wsize, ysize;
    char *w = read_all(win, &wsize);
    void *y = read_all(yin, &ysize);
    size_t wblock, yblock, per;
    vec_dot_fn fn;
    if (!strcmp(type, "q4_K")) { fn = ggml_vec_dot_q4_K_q8_K; wblock = sizeof(block_q4_K); yblock = sizeof(block_q8_K); per = QK_K; }
    else if (!strcmp(type, "q5_K")) { fn = ggml_vec_dot_q5_K_q8_K; wblock = sizeof(block_q5_K); yblock = sizeof(block_q8_K); per = QK_K; }
    else if (!strcmp(type, "q6_K")) { fn = ggml_vec_dot_q6_K_q8_K; wblock = sizeof(block_q6_K); yblock = sizeof(block_q8_K); per = QK_K; }
    else if (!strcmp(type, "q8_0")) { fn = ggml_vec_dot_q8_0_q8_0; wblock = sizeof(block_q8_0); yblock = sizeof(block_q8_0); per = QK8_0; }
    else { fprintf(stderr, "unknown type %s\n", type); return 2; }
    if (ysize == 0 || ysize % yblock) { fprintf(stderr, "activation is not whole blocks\n"); return 2; }
    size_t nblocks = ysize / yblock;
    size_t row = nblocks * wblock;
    if (wsize % row) { fprintf(stderr, "weights are not whole rows\n"); return 2; }
    size_t rows = wsize / row;
    float *s = malloc(rows * sizeof(float) + 1);
    for (size_t r = 0; r < rows; r++) fn((int) (nblocks * per), &s[r], 0, w + r * row, 0, y, 0, 1);
    write_all(out, s, rows * sizeof(float));
    return 0;
}

void gm_init_tables(void);

int main(int argc, char **argv) {
    gm_init_tables();
    if (argc == 5 && !strcmp(argv[1], "deq")) return deq(argv[2], argv[3], argv[4]);
    if (argc == 5 && !strcmp(argv[1], "quant")) return quant(argv[2], argv[3], argv[4]);
    if (argc == 6 && !strcmp(argv[1], "dot")) return dot(argv[2], argv[3], argv[4], argv[5]);
    fprintf(stderr, "usage: gm_harness deq TYPE IN OUT | quant q8_K|q8_0 IN OUT | dot TYPE W Y OUT\n");
    return 2;
}
