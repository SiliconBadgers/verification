`timescale 1ns / 1ps

package sb_mac_pkg;
  import uvm_pkg::*;
  import sb_uvm_base_pkg::*;
  `include "uvm_macros.svh"

  import "DPI-C" function int unsigned sb_mac_next(
    input int unsigned accumulator,
    input int signed   a,
    input int signed   b,
    input int unsigned rst_n,
    input int unsigned clear,
    input int unsigned enable
  );

  `include "agent/sb_mac_item.svh"
  `include "agent/sb_mac_driver.svh"
  `include "agent/sb_mac_input_monitor.svh"
  `include "agent/sb_mac_output_monitor.svh"
  `include "agent/sb_mac_agent.svh"
  `include "environment/sb_mac_predictor.svh"
  `include "environment/sb_mac_coverage.svh"
  `include "environment/sb_mac_scoreboard.svh"
  `include "environment/sb_mac_env.svh"
  `include "agent/sb_mac_sequence.svh"
  `include "test/sb_mac_base_test.svh"
  `include "test/sb_mac_smoke_test.svh"
  `include "test/sb_mac_random_test.svh"
  `include "test/sb_mac_overflow_test.svh"
endpackage
