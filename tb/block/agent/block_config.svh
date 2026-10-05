class block_config extends sb_agent_config;
  `uvm_object_utils(block_config)
  virtual block_if vif;
  int unsigned response_stall_cycles = 3;
  int unsigned max_wait_cycles = 200;
  function new(string name = "block_config");
    super.new(name);
  endfunction
endclass
