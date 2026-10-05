`timescale 1ns / 1ps
`include "uvm_macros.svh"

module sb_mac_top;
  import uvm_pkg::*;
  import sb_mac_pkg::*;
  logic clk = 0;
  sb_mac_if mac_if (clk);

  pe_mac dut (
    .clk(clk),
    .rst_n(mac_if.rst_n),
    .clear(mac_if.clear),
    .enable(mac_if.enable),
    .a(mac_if.a),
    .b(mac_if.b),
    .acc(mac_if.acc)
  );

  always #5ns clk = ~clk;

  initial begin
    uvm_config_db#(virtual sb_mac_if)::set(null, "uvm_test_top.*", "vif", mac_if);
    run_test();
  end

  initial begin
    int unsigned timeout_ns;
    timeout_ns = 5_000_000;
    void'($value$plusargs("SB_TIMEOUT_NS=%d", timeout_ns));
    if (timeout_ns == 0) `uvm_fatal("SB_TIMEOUT_CONFIG", "timeout must be positive")
    #(timeout_ns * 1ns);
    `uvm_fatal("SB_TIMEOUT", "MAC pilot watchdog expired")
  end

  initial begin
    // verilog_lint: waive plusarg-assignment -- Presence-only boolean switch.
    if ($test$plusargs("SB_FSDB")) begin
`ifdef SB_FSDB
      $fsdbDumpfile("waves.fsdb");
      $fsdbDumpvars(0, sb_mac_top);
`else
      `uvm_fatal("SB_FSDB_CONFIG", "recompile with SB_FSDB and the site Verdi PLI")
`endif
    end
  end
endmodule
