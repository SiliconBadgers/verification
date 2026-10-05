class tc_block_random extends test_top;
  `uvm_component_utils(tc_block_random)
  function new(string name, uvm_component parent);
    super.new(name, parent);
    random_data = 1;
    item_count  = 100;
  endfunction
endclass
