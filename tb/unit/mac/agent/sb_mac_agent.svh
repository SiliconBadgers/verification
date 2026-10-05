// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_agent extends uvm_agent;
  `uvm_component_utils(sb_mac_agent)
  uvm_sequencer #(sb_mac_item) sequencer;
  sb_mac_driver driver;
  sb_mac_input_monitor input_monitor;
  sb_mac_output_monitor output_monitor;
  sb_agent_config cfg;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (uvm_config_db#(sb_agent_config)::get(this, "", "config", cfg)) is_active = cfg.is_active;
    input_monitor  = sb_mac_input_monitor::type_id::create("input_monitor", this);
    output_monitor = sb_mac_output_monitor::type_id::create("output_monitor", this);
    if (get_is_active() == UVM_ACTIVE) begin
      sequencer = uvm_sequencer#(sb_mac_item)::type_id::create("sequencer", this);
      driver = sb_mac_driver::type_id::create("driver", this);
    end
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if (get_is_active() == UVM_ACTIVE) driver.seq_item_port.connect(sequencer.seq_item_export);
  endfunction
endclass
