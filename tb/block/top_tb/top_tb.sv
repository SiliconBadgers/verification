`timescale 1ns / 1ps
`include "uvm_macros.svh"
module top_tb;
  import uvm_pkg::*;
  import verif_pkg::*;
  logic clk = 0;
  block_if block_if_inst (clk);
  block_stub dut (
    .clk(clk),
    .rst_n(block_if_inst.rst_n),
    .req_valid(block_if_inst.req_valid),
    .req_ready(block_if_inst.req_ready),
    .req_id(block_if_inst.req_id),
    .req_op(block_if_inst.req_op),
    .req_a(block_if_inst.req_a),
    .req_b(block_if_inst.req_b),
    .rsp_valid(block_if_inst.rsp_valid),
    .rsp_ready(block_if_inst.rsp_ready),
    .rsp_id(block_if_inst.rsp_id),
    .rsp_data(block_if_inst.rsp_data),
    .rsp_error(block_if_inst.rsp_error)
  );
  always #5ns clk = ~clk;
  initial begin
    repeat (3) @(negedge clk);
    block_if_inst.rst_n = 1;
  end
  initial begin
    uvm_config_db#(virtual block_if)::set(null, "uvm_test_top.*", "block_vif", block_if_inst);
    run_test();
  end
  initial begin
    int unsigned timeout_ns;
    timeout_ns = 100_000;
    void'($value$plusargs("SB_TIMEOUT_NS=%d", timeout_ns));
    if (timeout_ns == 0) `uvm_fatal("SB_TIMEOUT_CONFIG", "timeout must be positive")
    #(timeout_ns * 1ns);
    `uvm_fatal("SB_TIMEOUT", "block stub watchdog expired")
  end
  initial begin
    // verilog_lint: waive plusarg-assignment
    if ($test$plusargs("SB_FSDB")) begin
`ifdef SB_FSDB
      $fsdbDumpfile("waves.fsdb");
      $fsdbDumpvars(0, top_tb);
`else
      `uvm_fatal("SB_FSDB_CONFIG", "recompile with --waves")
`endif
    end
  end
endmodule
