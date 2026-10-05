`timescale 1ns / 1ps

// Protocol-independent checking. Agents and reference models remain block-specific.
package sb_uvm_base_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"
`uvm_analysis_imp_decl(_sb_expected)
  `uvm_analysis_imp_decl(_sb_actual)

  class sb_agent_config extends uvm_object;
    `uvm_object_utils(sb_agent_config)
    uvm_active_passive_enum is_active = UVM_ACTIVE;

    function new(string name = "sb_agent_config");
      super.new(name);
    endfunction
  endclass

  // Publish a fresh, immutable ITEM on each analysis write. This checker allows
  // either stream to arrive first, but intentionally requires in-order results.
  // Subclass items_match() for protocol identity, reset epoch and payload semantics.
  class sb_in_order_scoreboard #(
    type ITEM = uvm_sequence_item
  ) extends uvm_scoreboard;
    `uvm_component_param_utils(sb_in_order_scoreboard#(ITEM))
    uvm_analysis_imp_sb_expected #(ITEM, sb_in_order_scoreboard #(ITEM)) expected;
    uvm_analysis_imp_sb_actual #(ITEM, sb_in_order_scoreboard #(ITEM)) actual;
    ITEM expected_queue[$];
    ITEM actual_queue[$];
    longint unsigned compared;
    longint unsigned mismatches;

    function new(string name, uvm_component parent);
      super.new(name, parent);
      expected = new("expected", this);
      actual   = new("actual", this);
    endfunction

    virtual function bit items_match(ITEM exp_item, ITEM got_item);
      `uvm_fatal("SB_COMPARE_POLICY", "subclass must define identity and payload comparison")
      return 0;
    endfunction

    virtual function string mismatch_description(ITEM exp_item, ITEM got_item);
      return "expected and actual transactions differ";
    endfunction

    virtual function void sample_actual(ITEM item);
    endfunction

    function void write_sb_expected(ITEM item);
      if (item == null) `uvm_fatal("SB_NULL_ITEM", "null expected observation")
      expected_queue.push_back(item);
      compare_available();
    endfunction

    function void write_sb_actual(ITEM item);
      if (item == null) `uvm_fatal("SB_NULL_ITEM", "null actual observation")
      actual_queue.push_back(item);
      sample_actual(item);
      compare_available();
    endfunction

    function void compare_available();
      ITEM exp_item;
      ITEM got_item;
      while (expected_queue.size() != 0 && actual_queue.size() != 0) begin
        exp_item = expected_queue.pop_front();
        got_item = actual_queue.pop_front();
        compared++;
        if (!items_match(exp_item, got_item)) begin
          mismatches++;
          `uvm_error("SB_MISMATCH", mismatch_description(exp_item, got_item))
        end
      end
    endfunction

    function void check_phase(uvm_phase phase);
      super.check_phase(phase);
      if (compared == 0) `uvm_error("SB_EMPTY", "scoreboard compared no observations")
      if (expected_queue.size() != 0 || actual_queue.size() != 0)
        `uvm_error("SB_UNDRAINED", "unmatched expected/actual observations remain")
    endfunction
  endclass
endpackage
