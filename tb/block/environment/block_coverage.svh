class block_coverage extends uvm_subscriber #(block_seqit);
  `uvm_component_utils(block_coverage)
  covergroup inputs_cg with function sample (block_seqit item);
    option.per_instance = 1;
    opcode: coverpoint item.op {bins add = {0}; bins xors = {1}; bins invalid[] = {2, 3};}
    operand: coverpoint item.a {bins zero = {0}; bins max = {32'hffffffff}; bins other = default;}
    commands: cross opcode, operand;
  endgroup
  function new(string name, uvm_component parent);
    super.new(name, parent);
    inputs_cg = new;
  endfunction
  function void write(block_seqit t);
    inputs_cg.sample(t);
  endfunction
endclass
