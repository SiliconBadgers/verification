`timescale 1ns / 1ps
`include "uvm_macros.svh"
module block_assertions (
  input logic clk,
  rst_n,
  req_valid,
  req_ready,
  rsp_valid,
  rsp_ready,
  input logic [15:0] req_id,
  rsp_id,
  input logic [1:0] req_op,
  input logic [31:0] req_a,
  req_b,
  rsp_data,
  input logic rsp_error
);
  import uvm_pkg::*;
  a_request_stable :
  assert property (@(posedge clk) disable iff(!rst_n)
    req_valid && !req_ready |=> req_valid && $stable(
    {req_id, req_op, req_a, req_b}
  ))
  else `uvm_error("SB_REQ_STABLE", "request changed while stalled")
  a_response_stable :
  assert property (@(posedge clk) disable iff(!rst_n)
    rsp_valid && !rsp_ready |=> rsp_valid && $stable(
    {rsp_id, rsp_data, rsp_error}
  ))
  else `uvm_error("SB_RSP_STABLE", "response changed while stalled")
  a_controls_known :
  assert property (@(posedge clk) disable iff (!rst_n) !$isunknown(
    {req_valid, req_ready, rsp_valid, rsp_ready}
  ))
  else `uvm_error("SB_CONTROL_X", "unknown handshake")
  a_one_outstanding :
  assert property (@(posedge clk) disable iff (!rst_n) rsp_valid |-> !req_ready)
  else `uvm_error("SB_OUTSTANDING", "stub accepted work while response owned")
  always @(negedge rst_n) begin
    #1ps;
    a_reset :
    assert (rsp_valid === 0)
    else `uvm_error("SB_RESET", "stub response valid did not clear")
  end
endmodule
bind block_stub block_assertions checks (.*);
