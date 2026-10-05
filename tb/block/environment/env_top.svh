class env_top extends uvm_env;
  `uvm_component_utils(env_top)
  block_config cfg;
  block_agent agent_h;
  block_predictor predictor_h;
  block_scoreboard scoreboard_h;
  block_coverage coverage_h;
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(block_config)::get(this, "", "config", cfg))
      cfg = block_config::type_id::create("cfg");
    if (!uvm_config_db#(virtual block_if)::get(this, "", "block_vif", cfg.vif))
      `uvm_fatal("SB_VIF", "cannot get block_vif")
    uvm_config_db#(block_config)::set(this, "agent_h", "config", cfg);
    agent_h = block_agent::type_id::create("agent_h", this);
    predictor_h = block_predictor::type_id::create("predictor_h", this);
    scoreboard_h = block_scoreboard::type_id::create("scoreboard_h", this);
    coverage_h = block_coverage::type_id::create("coverage_h", this);
  endfunction
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    agent_h.input_monitor_h.monitor_port.connect(predictor_h.analysis_export);
    agent_h.input_monitor_h.monitor_port.connect(coverage_h.analysis_export);
    agent_h.output_monitor_h.monitor_port.connect(scoreboard_h.actual);
    predictor_h.expected.connect(scoreboard_h.expected);
  endfunction
endclass
