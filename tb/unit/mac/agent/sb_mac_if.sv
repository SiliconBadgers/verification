`timescale 1ns / 1ps

interface sb_mac_if (
  input logic clk
);
  logic rst_n = 0;
  logic clear = 0;
  logic enable = 0;
  logic signed [7:0] a = 0;
  logic signed [7:0] b = 0;
  logic signed [31:0] acc;
endinterface
