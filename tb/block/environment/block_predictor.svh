class block_predictor extends uvm_subscriber #(block_seqit);
  `uvm_component_utils(block_predictor)
  uvm_analysis_port #(block_seqit) expected;
  bit injected;
  function new(string name, uvm_component parent);
    super.new(name, parent);
    expected = new("expected", this);
  endfunction
  function void write(block_seqit t);
    block_seqit item;
    item = block_seqit::type_id::create("item");
    item.id = t.id;
    item.error = (t.op >= 2);
    item.data = sb_block_expected(int'(t.op), t.a, t.b);
    // verilog_lint: waive plusarg-assignment
    if ($test$plusargs("SB_INJECT_MISMATCH") && !injected) begin
      item.data ^= 32'h1;
      injected = 1;
    end
    expected.write(item);
  endfunction
endclass
