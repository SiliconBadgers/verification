class test_top extends uvm_test;
  `uvm_component_utils(test_top)
  env_top env_h;
  int unsigned item_count = 12;
  bit random_data;
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    env_h = env_top::type_id::create("env_h", this);
  endfunction
  task run_phase(uvm_phase phase);
    block_sequence seq;
    phase.raise_objection(this);
    seq = block_sequence::type_id::create("seq");
    seq.count = item_count;
    seq.random_data = random_data;
    seq.start(env_h.agent_h.sequencer_h);
    // verilog_lint: waive plusarg-assignment
    if ($test$plusargs("SB_INJECT_TIMEOUT")) wait (1'b0);
    // Account for every submitted request, including missing requests/outputs.
    repeat (200) begin
      @(posedge env_h.cfg.vif.clk);
      #1ps;
      if (env_h.scoreboard_h.compared == item_count) break;
    end
    if (env_h.scoreboard_h.compared != item_count)
      `uvm_fatal("SB_TIMEOUT", "not all submitted work completed before drain deadline")
    // Check reset/reuse only after all accepted stub work has retired.
    @(negedge env_h.cfg.vif.clk);
    env_h.cfg.vif.rst_n = 0;
    #2ns;
    if (env_h.cfg.vif.rsp_valid !== 0) `uvm_error("SB_RESET", "stub reset failed")
    env_h.cfg.vif.rst_n = 1;
    seq.count = 4;
    seq.random_data = 0;
    seq.start(env_h.agent_h.sequencer_h);
    item_count += 4;
    repeat (200) begin
      @(posedge env_h.cfg.vif.clk);
      #1ps;
      if (env_h.scoreboard_h.compared == item_count) break;
    end
    if (env_h.scoreboard_h.compared != item_count)
      `uvm_fatal("SB_TIMEOUT", "post-reset drain failed")
    repeat (2) @(posedge env_h.cfg.vif.clk);
    #1ps;
    phase.drop_objection(this);
  endtask
  function void check_phase(uvm_phase phase);
    super.check_phase(phase);
    if (env_h.agent_h.input_monitor_h.accepted!=item_count ||
        env_h.agent_h.output_monitor_h.accepted!=item_count ||
        env_h.scoreboard_h.compared!=item_count)
      `uvm_error("SB_COUNT", "submitted/accepted/observed counts differ")
    if (env_h.agent_h.output_monitor_h.stalled == 0)
      `uvm_error("SB_NO_STALL", "test must exercise response backpressure")
  endfunction
  function void report_phase(uvm_phase phase);
    uvm_report_server server;
    super.report_phase(phase);
    server = uvm_report_server::get_server();
    if (env_h.scoreboard_h.compared>0 && env_h.scoreboard_h.mismatches==0 &&
        server.get_severity_count(
        UVM_ERROR
      ) == 0 && server.get_severity_count(
        UVM_FATAL
      ) == 0)
      `uvm_info("SB_TEST_PASS", $sformatf(
                "compared=%0d scope=PROVISIONAL_BLOCK_STUB", env_h.scoreboard_h.compared), UVM_NONE)
    else `uvm_error("SB_TEST_FAIL", "block stub test did not meet pass criteria")
  endfunction
endclass
