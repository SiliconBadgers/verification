class block_driver extends uvm_driver #(block_seqit);
  `uvm_component_utils(block_driver)
  block_config cfg;
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(block_config)::get(this, "", "config", cfg))
      `uvm_fatal("SB_CONFIG", "block driver needs config")
  endfunction
  task run_phase(uvm_phase phase);
    wait (cfg.vif.rst_n === 1'b1);
    fork
      drive_requests();
      drive_response_ready();
    join
  endtask
  task drive_requests();
    int unsigned cycles;
    forever begin
      seq_item_port.get_next_item(req);
      @(negedge cfg.vif.clk);
      cfg.vif.req_id = req.id;
      cfg.vif.req_op = req.op;
      cfg.vif.req_a = req.a;
      cfg.vif.req_b = req.b;
      cfg.vif.req_valid = 1;
      cycles = 0;
      do begin
        @(posedge cfg.vif.clk);
        cycles++;
        if (cycles > cfg.max_wait_cycles) `uvm_fatal("SB_TIMEOUT", "request acceptance timed out")
      end while (cfg.vif.req_ready !== 1'b1);
      @(negedge cfg.vif.clk);
      cfg.vif.req_valid = 0;
      seq_item_port.item_done();
    end
  endtask
  task drive_response_ready();
    forever begin
      @(negedge cfg.vif.clk);
      cfg.vif.rsp_ready = 0;
      repeat (cfg.response_stall_cycles) @(negedge cfg.vif.clk);
      cfg.vif.rsp_ready = 1;
    end
  endtask
endclass
