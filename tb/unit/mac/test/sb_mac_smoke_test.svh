// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_smoke_test extends sb_mac_base_test;
  `uvm_component_utils(sb_mac_smoke_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
    sequence_mode = 0;
  endfunction
endclass
