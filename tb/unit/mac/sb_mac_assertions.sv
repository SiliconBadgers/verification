`timescale 1ns / 1ps
`include "uvm_macros.svh"

// Bound to the real RTL instance. UVM reports make assertion failures visible
// to the same error-count gate used by the regression runner.
module sb_mac_assertions (
  input logic clk,
  input logic rst_n,
  input logic clear,
  input logic enable,
  input logic signed [7:0] a,
  input logic signed [7:0] b,
  input logic signed [31:0] acc
);
  import uvm_pkg::*;

  a_clear :
  assert property (@(posedge clk) disable iff (!rst_n) clear |=> acc == 0)
  else `uvm_error("SB_SVA_CLEAR", "clear must win over enable")

  a_hold :
  assert property (@(posedge clk) disable iff (!rst_n) !clear && !enable |=> $stable(acc))
  else `uvm_error("SB_SVA_HOLD", "disabled accumulator must hold")

  a_known_controls :
  assert property (@(posedge clk) !$isunknown({rst_n, clear, enable, a, b}))
  else `uvm_error("SB_SVA_INPUT_X", "unknown MAC inputs")

  a_known_output :
  assert property (@(negedge clk) !$isunknown(acc))
  else `uvm_error("SB_SVA_OUTPUT_X", "unknown MAC output")

  // Check after the reset NBA even when no rising clock occurs during reset.
  always @(negedge rst_n) begin
    #1ps;
    a_async_reset :
    assert (acc === 32'b0)
    else `uvm_error("SB_SVA_RESET", "asynchronous reset must clear acc")
  end
endmodule

bind pe_mac sb_mac_assertions mac_assertions (.*);
