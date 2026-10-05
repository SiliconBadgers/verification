// Contract: architecture/contracts/mac-v0.json (siliconbadgers.mac.v0).
// Arithmetic is defined in C++ integer space, without RTL widths/concatenations.
#include <cstdint>
#include <limits>

static_assert(std::numeric_limits<unsigned int>::digits == 32,
              "SystemVerilog DPI int unsigned requires a 32-bit unsigned int");
static_assert(std::numeric_limits<int>::digits == 31,
              "SystemVerilog DPI int requires a 32-bit signed int");

extern "C" unsigned int sb_mac_next(unsigned int accumulator, int a, int b,
                                     unsigned int rst_n, unsigned int clear,
                                     unsigned int enable) {
  if (rst_n == 0 || clear != 0) return 0;
  if (enable == 0) return accumulator;
  // a,b are sign-extended INT8 values. Their product cannot overflow int32_t.
  const std::int32_t product = a * b;
  // Conversion and addition in unsigned space define modulo-2^32 wrap, avoiding
  // undefined signed overflow and implementation-defined unsigned->signed casts.
  return accumulator + static_cast<std::uint32_t>(product);
}
