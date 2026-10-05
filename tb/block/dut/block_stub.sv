`timescale 1ns / 1ps
// Behavioral plumbing stub ONLY. One outstanding request, no DMA or state.
// op=0: modulo-2^32 add; op=1: XOR; op=2/3: error with zero data.
module block_stub (
  input logic clk,
  rst_n,
  req_valid,
  rsp_ready,
  input logic [15:0] req_id,
  input logic [1:0] req_op,
  input logic [31:0] req_a,
  req_b,
  output logic req_ready,
  rsp_valid,
  output logic [15:0] rsp_id,
  output logic [31:0] rsp_data,
  output logic rsp_error
);
  assign req_ready = rst_n && !rsp_valid;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rsp_valid <= 0;
      rsp_id <= 0;
      rsp_data <= 0;
      rsp_error <= 0;
    end else if (rsp_valid && rsp_ready) begin
      rsp_valid <= 0;
    end else if (req_valid && req_ready) begin
      rsp_valid <= 1;
      rsp_id <= req_id;
      rsp_error <= req_op[1];
      case (req_op)
        0: rsp_data <= req_a + req_b;
        1: rsp_data <= req_a ^ req_b;
        default: rsp_data <= 0;
      endcase
    end
  end
endmodule
