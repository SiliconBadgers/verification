# Independent reference models

[Home](../README.md)

`block_stub_reference.cpp` implements only the temporary add/XOR/error oracle;
`block_stub_reference_test.cpp` checks 100 opcode/boundary combinations.
`mac_reference.cpp` implements the onboarding MAC contract with defined unsigned
32-bit wrap; `mac_reference_test.cpp` checks 327,680 arithmetic vectors plus
priority/overflow cases. Each model receives observed inputs, never DUT outputs.

Build either pair with `g++ -std=c++11 -Wall -Wextra -Werror -fsanitize=undefined`
and `-o build/model/<test>`. Model passes are not RTL or VCS evidence.
