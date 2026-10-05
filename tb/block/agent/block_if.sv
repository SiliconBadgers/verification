`timescale 1ns / 1ps
// TEMPORARY scaffold protocol, not an accelerator interface.
interface block_if (
  input logic clk
);
  logic rst_n = 0;
  logic req_valid = 0;
  logic req_ready;
  logic [15:0] req_id = 0;
  logic [1:0] req_op = 0;
  logic [31:0] req_a = 0;
  logic [31:0] req_b = 0;
  logic rsp_valid;
  logic rsp_ready = 0;
  logic [15:0] rsp_id;
  logic [31:0] rsp_data;
  logic rsp_error;
endinterface
