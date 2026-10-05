// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_input_monitor extends uvm_monitor;
  `uvm_component_utils(sb_mac_input_monitor)
  virtual sb_mac_if vif;
  uvm_analysis_port #(sb_mac_item) observed;
  longint unsigned next_id;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    observed = new("observed", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual sb_mac_if)::get(this, "", "vif", vif))
      `uvm_fatal("SB_VIF", "MAC input monitor needs vif")
  endfunction

  task run_phase(uvm_phase phase);
    sb_mac_item item;
    forever begin
      @(posedge vif.clk or negedge vif.rst_n);
      item = sb_mac_item::type_id::create("item");
      item.event_id = next_id++;
      // The driver established these pins on the preceding falling edge.
      // At a rising edge, snapshot before the DUT's accumulator NBA update.
      item.a = vif.a;
      item.b = vif.b;
      item.rst_n = vif.rst_n;
      item.clear = vif.clear;
      item.enable = vif.enable;
      if ($isunknown({item.rst_n, item.clear, item.enable, item.a, item.b}))
        `uvm_fatal("SB_INPUT_X", "cannot predict unknown observed MAC inputs")
      observed.write(item);
    end
  endtask
endclass
