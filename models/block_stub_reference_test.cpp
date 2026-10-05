// Oracle checks for temporary infrastructure plumbing, not accelerator kernels.
#include <cstdint>
#include <cstdlib>
#include <iostream>
extern "C" unsigned int sb_block_expected(unsigned int, unsigned int, unsigned int);
int main() {
  const unsigned int values[] = {0, 1, 0x7fffffffU, 0x80000000U, 0xffffffffU};
  unsigned count = 0;
  for (unsigned op=0; op<4; ++op) {
    for (auto a : values) for (auto b : values) {
      std::uint32_t expected=0;
      if (op==0) expected=static_cast<std::uint32_t>((static_cast<std::uint64_t>(a)+b) % (1ULL<<32));
      if (op==1) {
        // Construct XOR one bit at a time, independent of the oracle expression.
        for (unsigned bit=0; bit<32; ++bit)
          if (((a>>bit)&1U) != ((b>>bit)&1U)) expected |= 1U<<bit;
      }
      if (sb_block_expected(op,a,b)!=expected) { std::cerr << "FAIL block oracle\n"; return 1; }
      ++count;
    }
  }
  std::cout << "PASS block_stub_reference: " << count << " boundary/opcode cases\n";
}
