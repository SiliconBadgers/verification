`timescale 1ns / 1ps
package verif_pkg;
  import uvm_pkg::*;
  import sb_uvm_base_pkg::*;
  import block_pkg::*;
  `include "uvm_macros.svh"
  import "DPI-C" function int unsigned sb_block_expected(
    input int unsigned op,
    input int unsigned a,
    input int unsigned b
  );
  `include "environment/block_predictor.svh"
  `include "environment/block_scoreboard.svh"
  `include "environment/block_coverage.svh"
  `include "environment/env_top.svh"
  `include "test/test_top.svh"
  `include "test/tc_block_smoke.svh"
  `include "test/tc_block_random.svh"
endpackage
