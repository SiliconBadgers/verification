class block_seqit extends uvm_sequence_item;
  `uvm_object_utils(block_seqit)
  rand bit [1:0] op;
  rand bit [31:0] a;
  rand bit [31:0] b;
  logic [15:0] id;
  logic [31:0] data;
  logic error;
  function new(string name = "block_seqit");
    super.new(name);
  endfunction
endclass
