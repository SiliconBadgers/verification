// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_scoreboard extends sb_in_order_scoreboard #(sb_mac_item);
  `uvm_component_utils(sb_mac_scoreboard)

  covergroup actual_cg with function sample (logic [31:0] value);
    option.per_instance = 1;
    result: coverpoint value {
      bins zero = {0};
      bins positive = {[1 : 32'h7fff_ffff]};
      bins negative = {[32'h8000_0000 : 32'hffff_ffff]};
    }
  endgroup

  function new(string name, uvm_component parent);
    super.new(name, parent);
    actual_cg = new;
  endfunction

  virtual function bit items_match(sb_mac_item exp_item, sb_mac_item got_item);
    return exp_item.event_id == got_item.event_id && got_item.value === exp_item.value;
  endfunction

  virtual function string mismatch_description(sb_mac_item exp_item, sb_mac_item got_item);
    return $sformatf(
      "expected event=%0d acc=%08h; actual event=%0d acc=%08h",
      exp_item.event_id,
      exp_item.value,
      got_item.event_id,
      got_item.value
    );
  endfunction

  virtual function void sample_actual(sb_mac_item item);
    actual_cg.sample(item.value);
  endfunction
endclass
