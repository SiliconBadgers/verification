// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_base_test extends uvm_test;
  `uvm_component_utils(sb_mac_base_test)
  sb_mac_env env;
  int sequence_mode;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    env = sb_mac_env::type_id::create("env", this);
  endfunction

  task run_phase(uvm_phase phase);
    sb_mac_sequence seq;
    phase.raise_objection(this);
    seq = sb_mac_sequence::type_id::create("seq");
    seq.mode = sequence_mode;
    seq.start(env.agent.sequencer);
    // verilog_lint: waive plusarg-assignment -- Presence-only boolean switch.
    if ($test$plusargs("SB_INJECT_TIMEOUT")) wait (1'b0);
    repeat (2) @(posedge env.agent.driver.vif.clk);
    #2ps;
    phase.drop_objection(this);
  endtask

  function void check_phase(uvm_phase phase);
    super.check_phase(phase);
    if (sequence_mode == 2 &&

        (env.predictor.positive_wraps == 0 || env.predictor.negative_wraps == 0))
      `uvm_error("SB_OVERFLOW_MISSING", "overflow test must exercise both wrap directions")
  endfunction

  function void report_phase(uvm_phase phase);
    uvm_report_server server;
    super.report_phase(phase);
    server = uvm_report_server::get_server();
    if (env.scoreboard.compared > 0 && env.scoreboard.mismatches == 0 && server.get_severity_count(
        UVM_ERROR
      ) == 0 && server.get_severity_count(
        UVM_FATAL
      ) == 0)
      `uvm_info("SB_TEST_PASS", $sformatf(
                "compared=%0d positive_wraps=%0d negative_wraps=%0d",
                env.scoreboard.compared,
                env.predictor.positive_wraps,
                env.predictor.negative_wraps
                ), UVM_NONE)
    else `uvm_error("SB_TEST_FAIL", "MAC pilot did not meet pass criteria")
  endfunction
endclass
