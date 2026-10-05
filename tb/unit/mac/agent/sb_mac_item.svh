// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_item extends uvm_sequence_item;
  `uvm_object_utils(sb_mac_item)
  rand logic signed [7:0] a;
  rand logic signed [7:0] b;
  rand logic enable;
  rand logic clear;
  bit pulse_reset;
  logic rst_n;
  longint unsigned event_id;
  logic [31:0] value;

  function new(string name = "sb_mac_item");
    super.new(name);
  endfunction
endclass
