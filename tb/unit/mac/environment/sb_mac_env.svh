// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_env extends uvm_env;
  `uvm_component_utils(sb_mac_env)
  sb_mac_agent agent;
  sb_mac_predictor predictor;
  sb_mac_coverage coverage;
  sb_mac_scoreboard scoreboard;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    agent = sb_mac_agent::type_id::create("agent", this);
    predictor = sb_mac_predictor::type_id::create("predictor", this);
    coverage = sb_mac_coverage::type_id::create("coverage", this);
    scoreboard = sb_mac_scoreboard::type_id::create("scoreboard", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    agent.input_monitor.observed.connect(predictor.analysis_export);
    agent.input_monitor.observed.connect(coverage.analysis_export);
    agent.output_monitor.observed.connect(scoreboard.actual);
    predictor.expected.connect(scoreboard.expected);
  endfunction
endclass
