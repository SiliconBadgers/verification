`timescale 1ns/1ps

// Starter verification example for the existing pe_mac. The integer scoreboard
// wraps at 32 bits, matching the RTL; it does not saturate the accumulator.
module pe_mac_smoke_tb;
    reg clk = 0;
    reg rst_n = 1;
    reg clear = 0;
    reg enable = 0;
    reg signed [7:0] a = 0;
    reg signed [7:0] b = 0;
    wire signed [31:0] acc;
    integer expected = 0;
    integer checks = 0;
    integer i;
    integer fd;
    integer read_count;
    integer golden_checks = 0;
    integer ga, gb, ge, gc, expected_from_model;
    string vector_path;

    pe_mac dut(.*);
    always #5 clk = ~clk;

    task automatic check_output;
        if (acc !== expected)
            $fatal(1, "MAC mismatch check=%0d actual=%0d expected=%0d", checks, acc, expected);
        checks = checks + 1;
    endtask

    task automatic tick(input integer av, input integer bv,
                        input bit en, input bit clr);
        @(negedge clk);
        a = av;
        b = bv;
        enable = en;
        clear = clr;
        if (clr) expected = 0;
        else if (en) expected = expected + av * bv;
        @(posedge clk);
        #1;
        check_output();
    endtask

    initial begin
        // Assert reset between clock edges: reset is asynchronous.
        #1 rst_n = 0;
        #1 check_output();
        @(negedge clk) rst_n = 1;
        if (!$value$plusargs("VECTORS=%s", vector_path)) $fatal(1, "Missing VECTORS");
        fd = $fopen(vector_path, "r");
        if (fd == 0) $fatal(1, "Cannot open golden vectors");
        read_count = $fscanf(fd, "%d %d %d %d %d", ga, gb, ge, gc, expected_from_model);
        while (read_count == 5) begin
            tick(ga, gb, ge != 0, gc != 0);
            if (acc !== expected_from_model) $fatal(1, "Golden mismatch row=%0d", golden_checks);
            golden_checks = golden_checks + 1;
            read_count = $fscanf(fd, "%d %d %d %d %d", ga, gb, ge, gc, expected_from_model);
        end
        if (golden_checks == 0 || (read_count != -1 && !(read_count == 0 && $feof(fd))))
            $fatal(1, "Malformed/empty golden vectors");
        $fclose(fd);
        $display("PASS golden vectors checked=%0d", golden_checks);
        tick(0, 0, 0, 1);
        tick(-128, -128, 1, 0);
        tick(127, -128, 1, 0);
        tick(127, 127, 0, 0); // disabled must hold
        tick(127, 127, 1, 1); // clear wins over enable
        tick(-1, 127, 1, 0);
        for (i = 0; i < 256; i = i + 1)
            tick((i * 37) % 256 - 128, (i * 73) % 256 - 128, i % 7 != 0, i % 31 == 0);
        tick(0, 0, 0, 1);
        // Cross signed INT32 overflow with valid INT8 products.
        for (i = 0; i < 131073; i = i + 1)
            tick(-128, -128, 1, 0);
        if (expected != -2147467264) $fatal(1, "Overflow stimulus failed");
        // Mid-operation asynchronous reset must clear a nonzero accumulator.
        #1 rst_n = 0;
        expected = 0;
        #1 check_output();
        enable = 0;
        clear = 0;
        @(negedge clk) rst_n = 1;
        tick(3, -7, 1, 0);
        $display("PASS pe_mac_smoke checks=%0d (signed products, hold, clear, reset, overflow)", checks);
        $finish;
    end

    initial begin
        #2000000;
        $fatal(1, "TIMEOUT pe_mac_smoke");
    end
endmodule
