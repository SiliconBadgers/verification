// Independent oracle for TEMPORARY block-stub plumbing only.
#include <cstdint>
#include <limits>
static_assert(std::numeric_limits<unsigned int>::digits == 32, "DPI unsigned int width");
extern "C" unsigned int sb_block_expected(unsigned int op, unsigned int a, unsigned int b) {
  if (op == 0) return static_cast<std::uint32_t>(static_cast<std::uint64_t>(a) + b);
  if (op == 1) return a ^ b;
  return 0;
}
