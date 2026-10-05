class block_agent extends uvm_agent;
  `uvm_component_utils(block_agent)
  block_config cfg;
  block_sequencer sequencer_h;
  block_driver driver_h;
  block_monitor input_monitor_h;
  block_monitor output_monitor_h;
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(block_config)::get(this, "", "config", cfg))
      `uvm_fatal("SB_CONFIG", "block agent needs config")
    uvm_config_db#(block_config)::set(this, "*", "config", cfg);
    is_active = cfg.is_active;
    input_monitor_h = block_monitor::type_id::create("input_monitor_h", this);
    output_monitor_h = block_monitor::type_id::create("output_monitor_h", this);
    output_monitor_h.response_side = 1;
    if (is_active == UVM_ACTIVE) begin
      sequencer_h = block_sequencer::type_id::create("sequencer_h", this);
      driver_h = block_driver::type_id::create("driver_h", this);
    end
  endfunction
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if (is_active == UVM_ACTIVE) driver_h.seq_item_port.connect(sequencer_h.seq_item_export);
  endfunction
endclass
