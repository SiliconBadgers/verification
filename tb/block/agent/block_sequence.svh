class block_sequence extends uvm_sequence #(block_seqit);
  `uvm_object_utils(block_sequence)
  int unsigned count = 12;
  bit random_data;
  function new(string name = "block_sequence");
    super.new(name);
  endfunction
  task body();
    block_seqit item;
    for (int unsigned i = 0; i < count; i++) begin
      item = block_seqit::type_id::create("item");
      start_item(item);
      if (random_data) begin
        if (!item.randomize()) `uvm_fatal("SB_RANDOMIZE", "block item randomization failed")
      end else begin
        item.op = 2'(i % 4);
        item.a  = (i < 4) ? 32'hffffffff : 32'(i);
        item.b  = 32'(i + 1);
      end
      item.id = 16'(i);
      finish_item(item);
    end
  endtask
endclass
