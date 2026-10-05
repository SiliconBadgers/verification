class block_scoreboard extends sb_in_order_scoreboard #(block_seqit);
  `uvm_component_utils(block_scoreboard)
  covergroup results_cg with function sample (bit error, logic [31:0] data);
    option.per_instance = 1;
    status: coverpoint error;
    value: coverpoint data {bins zero = {0}; bins nonzero = default;}
  endgroup
  function new(string name, uvm_component parent);
    super.new(name, parent);
    results_cg = new;
  endfunction
  virtual function bit items_match(block_seqit exp_item, block_seqit got_item);
    return (exp_item.id === got_item.id) &&
        (exp_item.error === got_item.error) && (exp_item.data === got_item.data);
  endfunction
  virtual function string mismatch_description(block_seqit exp_item, block_seqit got_item);
    return $sformatf(
      "id=%0d expected=%08h/%0b actual id=%0d data=%08h/%0b",
      exp_item.id,
      exp_item.data,
      exp_item.error,
      got_item.id,
      got_item.data,
      got_item.error
    );
  endfunction
  virtual function void sample_actual(block_seqit item);
    results_cg.sample(item.error, item.data);
  endfunction
endclass
