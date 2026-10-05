// Standalone contract checks; this does not compile or simulate any RTL/UVM.
#include <cstdint>
#include <cstdlib>
#include <iostream>

extern "C" unsigned int sb_mac_next(unsigned int, int, int, unsigned int,
                                     unsigned int, unsigned int);

static void check(bool condition, const char* message) {
  if (!condition) {
    std::cerr << "FAIL " << message << '\n';
    std::exit(1);
  }
}

int main() {
  check(sb_mac_next(19, -128, -128, 0, 0, 1) == 0, "reset priority");
  check(sb_mac_next(19, -128, -128, 1, 1, 1) == 0, "clear priority");
  check(sb_mac_next(19, -128, -128, 1, 0, 0) == 19, "disabled hold");
  // Exhaust all 65,536 operand pairs against an int64 calculation and compare
  // bit patterns. Nonzero seeds exercise carry and wrap in either direction.
  const std::uint32_t seeds[] = {0, 1, 0x7fffffffU, 0x80000000U, 0xffffffffU};
  for (auto seed : seeds) {
    for (int a = -128; a <= 127; ++a) {
      for (int b = -128; b <= 127; ++b) {
        const std::int64_t wide = static_cast<std::int64_t>(seed) +
                                  static_cast<std::int64_t>(a) * b;
        check(sb_mac_next(seed, a, b, 1, 0, 1) ==
                  static_cast<std::uint32_t>(wide),
              "exhaustive signed product / accumulator wrap");
      }
    }
  }
  check(sb_mac_next(0x7fffffffU, 1, 1, 1, 0, 1) == 0x80000000U,
        "positive signed overflow");
  check(sb_mac_next(0x80000000U, -1, 1, 1, 0, 1) == 0x7fffffffU,
        "negative signed overflow");
  std::cout << "PASS mac_reference: 327680 arithmetic vectors and priority checks\n";
}
