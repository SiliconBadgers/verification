// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_coverage extends uvm_subscriber #(sb_mac_item);
  `uvm_component_utils(sb_mac_coverage)

  covergroup inputs_cg with function sample (sb_mac_item item);
    option.per_instance = 1;
    reset: coverpoint item.rst_n;
    clear: coverpoint item.clear iff (item.rst_n);
    enable: coverpoint item.enable iff (item.rst_n);
    controls: cross clear, enable;
    operand_a: coverpoint item.a iff (item.rst_n && !item.clear && item.enable) {
      bins minimum = {-128};
      bins negative = {[-127 : -1]};
      bins zero = {0};
      bins positive = {[1 : 126]};
      bins maximum = {127};
    }
    operand_b: coverpoint item.b iff (item.rst_n && !item.clear && item.enable) {
      bins minimum = {-128};
      bins negative = {[-127 : -1]};
      bins zero = {0};
      bins positive = {[1 : 126]};
      bins maximum = {127};
    }
    operand_pairs: cross operand_a, operand_b;
  endgroup

  function new(string name, uvm_component parent);
    super.new(name, parent);
    inputs_cg = new;
  endfunction

  function void write(sb_mac_item t);
    inputs_cg.sample(t);
  endfunction
endclass
