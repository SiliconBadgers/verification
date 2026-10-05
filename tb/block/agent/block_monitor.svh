// Two independent monitors share a type, selected as request or response role.
class block_monitor extends uvm_monitor;
  `uvm_component_utils(block_monitor)
  block_config cfg;
  bit response_side;
  longint unsigned accepted;
  longint unsigned stalled;
  uvm_analysis_port #(block_seqit) monitor_port;
  function new(string name, uvm_component parent);
    super.new(name, parent);
    monitor_port = new("monitor_port", this);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(block_config)::get(this, "", "config", cfg))
      `uvm_fatal("SB_CONFIG", "block monitor needs config")
  endfunction
  task run_phase(uvm_phase phase);
    block_seqit item;
    forever begin
      // Snapshot pre-NBA: these are the pins accepted at THIS edge.
      @(posedge cfg.vif.clk);
      if (!cfg.vif.rst_n) continue;
      if (response_side) begin
        if (cfg.vif.rsp_valid && !cfg.vif.rsp_ready) stalled++;
        if (!(cfg.vif.rsp_valid && cfg.vif.rsp_ready)) continue;
        if ($isunknown({cfg.vif.rsp_id, cfg.vif.rsp_data, cfg.vif.rsp_error}))
          `uvm_fatal("SB_OUTPUT_X", "unknown accepted response")
        item = block_seqit::type_id::create("item");
        item.id = cfg.vif.rsp_id;
        item.data = cfg.vif.rsp_data;
        item.error = cfg.vif.rsp_error;
      end else begin
        if (cfg.vif.req_valid && !cfg.vif.req_ready) stalled++;
        if (!(cfg.vif.req_valid && cfg.vif.req_ready)) continue;
        if ($isunknown({cfg.vif.req_id, cfg.vif.req_op, cfg.vif.req_a, cfg.vif.req_b}))
          `uvm_fatal("SB_INPUT_X", "unknown accepted request")
        item = block_seqit::type_id::create("item");
        item.id = cfg.vif.req_id;
        item.op = cfg.vif.req_op;
        item.a = cfg.vif.req_a;
        item.b = cfg.vif.req_b;
      end
      accepted++;
      monitor_port.write(item);
    end
  endtask
endclass
