// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_sequence extends uvm_sequence #(sb_mac_item);
  `uvm_object_utils(sb_mac_sequence)
  int mode;

  function new(string name = "sb_mac_sequence");
    super.new(name);
  endfunction

  task send(int a, int b, bit enable = 1, bit clear = 0, bit pulse_reset = 0);
    sb_mac_item item;
    item = sb_mac_item::type_id::create("item");
    start_item(item);
    item.a = 8'(a);
    item.b = 8'(b);
    item.enable = enable;
    item.clear = clear;
    item.pulse_reset = pulse_reset;
    finish_item(item);
  endtask

  task body();
    sb_mac_item item;
    int unsigned random_cycles = 1000;
    int corners[5] = '{-128, -1, 0, 1, 127};
    send(0, 0, 0, 0, 1);
    foreach (corners[i]) begin
      foreach (corners[j]) send(corners[i], corners[j]);
    end
    send(3, -7);
    send(127, 127, 0);  // hold with changing operands

    send(-128, -128, 1, 1);  // clear wins over an enabled nonzero product

    send(127, -1);
    send(0, 0, 0, 1);  // clear while disabled

    send(-128, -128);  // ensure accumulator is nonzero before async reset

    send(0, 0, 0, 0, 1);  // short async pulse while no rising clock occurs

    send(3, -7);  // resume immediately after reset

    if (mode == 1) begin
      void'($value$plusargs("SB_RANDOM_CYCLES=%d", random_cycles));
      if (random_cycles == 0 || random_cycles > 100_000)
        `uvm_fatal("SB_RANDOM_CONFIG", "SB_RANDOM_CYCLES must be in [1,100000]")
      repeat (random_cycles) begin
        item = sb_mac_item::type_id::create("item");
        start_item(item);
        if (!item.randomize() with {
            enable dist {
              1 := 9,
              0 := 1
            };
            clear dist {
              1 := 1,
              0 := 31
            };
          })
          `uvm_fatal("SB_RANDOMIZE", "MAC randomization failed")
        finish_item(item);
      end
    end else if (mode == 2) begin
      send(0, 0, 0, 1);
      repeat (131073) send(-128, -128);  // cross INT32_MAX with real products

      send(0, 0, 0, 1);
      repeat (132106) send(-128, 127);  // cross INT32_MIN with real products

    end
    send(0, 0, 0);  // final idle item prevents extra accumulation during drain

  endtask
endclass
