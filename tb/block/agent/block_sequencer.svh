class block_sequencer extends uvm_sequencer #(block_seqit);
  `uvm_component_utils(block_sequencer)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
endclass
