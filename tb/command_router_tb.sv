module command_router_tb;
  timeunit 1ns; timeprecision 1ps;

  import command_pkg::*;

  logic clk = 1'b0;
  logic rst_n = 1'b0;
  logic quiesce = 1'b0;
  logic idle;
  logic cmd_valid = 1'b0;
  logic cmd_ready;
  logic completion_valid;
  logic completion_ready = 1'b0;
  command_t cmd;
  completion_t completion;

  always #5ns clk = ~clk;

  command_router_test_top u_dut (
    .clk_i(clk),
    .rst_ni(rst_n),
    .quiesce_i(quiesce),
    .idle_o(idle),
    .cmd_valid_i(cmd_valid),
    .cmd_ready_o(cmd_ready),
    .cmd_i(cmd),
    .completion_valid_o(completion_valid),
    .completion_ready_i(completion_ready),
    .completion_o(completion)
  );

  // Drive on falling edges and sample after rising-edge nonblocking updates.
  task automatic tick;
    @(posedge clk);
    #1ns;
  endtask

  task automatic check_command(input logic [15:0] opcode, input logic [31:0] sequence_id,
                               input completion_status_e expected);
    @(negedge clk);
    cmd = '0;
    cmd.abi_version = COMMAND_ABI_VERSION;
    cmd.opcode = opcode;
    cmd.sequence_id = sequence_id;
    cmd_valid = 1'b1;
    tick();
    @(negedge clk);
    cmd_valid = 1'b0;
    // Changing the input after acceptance must not change the held completion.
    cmd.sequence_id = sequence_id + 32'd99;
    repeat (4) begin
      tick();
      if (!completion_valid || cmd_ready || completion.sequence_id != sequence_id ||
          completion.status != expected) begin
        $fatal(1, "completion or backpressure failure");
      end
    end
    @(negedge clk);
    completion_ready = 1'b1;
    tick();
    @(negedge clk);
    completion_ready = 1'b0;
    tick();
    if (!idle || completion_valid) begin
      $fatal(1, "completion not released");
    end
  endtask

  initial begin
    cmd = '0;
    repeat (3) tick();
    @(negedge clk);
    rst_n = 1'b1;
    tick();
    check_command(OPCODE_MATRIX, 32'd1, StatusUnimplemented);
    check_command(OPCODE_VECTOR_TEST, 32'd2, StatusUnimplemented);
    check_command(OPCODE_STATE_TEST, 32'd3, StatusUnimplemented);
    check_command(OPCODE_MEMORY_TEST, 32'd4, StatusUnimplemented);
    check_command(16'hffff, 32'd5, StatusBadCommand);

    @(negedge clk);
    quiesce   = 1'b1;
    cmd_valid = 1'b1;
    tick();
    if (cmd_ready || completion_valid || !idle) begin
      $fatal(1, "quiesce accepted work");
    end
    @(negedge clk);
    quiesce   = 1'b0;
    cmd_valid = 1'b0;

    // Quiesce blocks new work while preserving the outstanding completion.
    @(negedge clk);
    cmd.abi_version = COMMAND_ABI_VERSION;
    cmd.opcode = OPCODE_MATRIX;
    cmd.sequence_id = 32'd6;
    cmd_valid = 1'b1;
    tick();
    @(negedge clk);
    quiesce = 1'b1;
    cmd.sequence_id = 32'd99;
    repeat (3) begin
      tick();
      if (cmd_ready || idle || !completion_valid || completion.sequence_id != 32'd6) begin
        $fatal(1, "quiesce lost owned command or accepted new work");
      end
    end
    @(negedge clk);
    completion_ready = 1'b1;
    tick();
    @(negedge clk);
    completion_ready = 1'b0;
    tick();
    if (cmd_ready || !idle || completion_valid) begin
      $fatal(1, "quiesce did not drain");
    end
    @(negedge clk);
    cmd_valid = 1'b0;
    quiesce   = 1'b0;
    check_command(OPCODE_MATRIX, 32'd7, StatusUnimplemented);

    @(negedge clk);
    cmd.abi_version = 16'd0;
    cmd.sequence_id = 32'd8;
    cmd_valid = 1'b1;
    tick();
    @(negedge clk);
    cmd_valid = 1'b0;
    tick();
    if (!completion_valid || completion.status != StatusBadCommand) begin
      $fatal(1, "ABI validation");
    end
    // Reset cancels fixture state. No external memory transaction is modeled here.
    @(negedge clk);
    rst_n = 1'b0;
    tick();
    if (completion_valid || !idle) begin
      $fatal(1, "reset did not flush fixture");
    end
    $display("PASS router: 8 commands, all routes, ABI error, backpressure, quiesce, reset");
    $finish;
  end

  initial begin
    #10000ns;
    $fatal(1, "timeout");
  end
endmodule
