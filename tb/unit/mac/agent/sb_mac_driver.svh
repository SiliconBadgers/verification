// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_driver extends uvm_driver #(sb_mac_item);
  `uvm_component_utils(sb_mac_driver)
  virtual sb_mac_if vif;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual sb_mac_if)::get(this, "", "vif", vif))
      `uvm_fatal("SB_VIF", "MAC driver needs vif")
  endfunction

  task run_phase(uvm_phase phase);
    forever begin
      seq_item_port.get_next_item(req);
      @(negedge vif.clk);
      vif.rst_n = 1;
      vif.a = req.a;
      vif.b = req.b;
      vif.enable = req.enable;
      vif.clear = req.clear;
      if (req.pulse_reset) begin
        #2ns;
        vif.rst_n = 0;
        #1ns;
        vif.rst_n = 1;
      end
      @(posedge vif.clk);
      // Output monitor samples at +1ps; item_done is later so the sequence
      // and end-of-test drain cannot overtake its last observation.
      #2ps;
      seq_item_port.item_done();
    end
  endtask
endclass
