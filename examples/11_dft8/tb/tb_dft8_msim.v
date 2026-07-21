`timescale 1ns / 1ps

module tb_dft8_top;
    reg clk = 0;
    reg rst_n = 0;
    reg start = 0;
    reg [15:0] sr0,sr1,sr2,sr3,sr4,sr5,sr6,sr7;
    reg [15:0] si0,si1,si2,si3,si4,si5,si6,si7;
    wire [15:0] fr0,fr1,fr2,fr3,fr4,fr5,fr6,fr7;
    wire [15:0] fi0,fi1,fi2,fi3,fi4,fi5,fi6,fi7;
    wire done;

    dft8_top dut(
        .clk(clk),.rst_n(rst_n),.start(start),
        .sr0(sr0),.sr1(sr1),.sr2(sr2),.sr3(sr3),.sr4(sr4),.sr5(sr5),.sr6(sr6),.sr7(sr7),
        .si0(si0),.si1(si1),.si2(si2),.si3(si3),.si4(si4),.si5(si5),.si6(si6),.si7(si7),
        .fr0(fr0),.fr1(fr1),.fr2(fr2),.fr3(fr3),.fr4(fr4),.fr5(fr5),.fr6(fr6),.fr7(fr7),
        .fi0(fi0),.fi1(fi1),.fi2(fi2),.fi3(fi3),.fi4(fi4),.fi5(fi5),.fi6(fi6),.fi7(fi7),
        .done(done)
    );

    always #5 clk = ~clk;

    integer i;
    integer fail = 0;

    task wait_done;
    begin
        i = 0;
        while (!done && i < 200) begin
            @(posedge clk); i = i + 1;
        end
        if (!done) begin
            $display("FAIL: DFT did not finish within 200 cycles");
            $stop;
        end
    end
    endtask

    task check_bin(input [15:0] actual, input [15:0] expected_real,
                   input [15:0] expected_imag, input [3:0] bin);
    begin
        if (actual !== expected_real) begin
            $display("FAIL bin[%0d] real: expected %d, got %d", bin, $signed(expected_real), $signed(actual));
            fail = fail + 1;
        end
    end
    endtask

    initial begin
        // reset
        rst_n = 0; start = 0;
        {sr0,sr1,sr2,sr3,sr4,sr5,sr6,sr7}=0;
        {si0,si1,si2,si3,si4,si5,si6,si7}=0;
        repeat(3) @(posedge clk);
        rst_n = 1;
        repeat(5) @(posedge clk);

        $display("=== Test 1: DC input ===");
        {sr0,sr1,sr2,sr3,sr4,sr5,sr6,sr7} = {16'd3277,16'd3277,16'd3277,16'd3277,16'd3277,16'd3277,16'd3277,16'd3277};
        start = 1; @(posedge clk); start = 0;
        wait_done;

        check_bin(fr0, 16'd26215, 0, 0);
        check_bin(fr1, 0, 0, 1);
        check_bin(fr2, 0, 0, 2);
        check_bin(fr3, 0, 0, 3);

        $display("=== Test 2: All zeros ===");
        {sr0,sr1,sr2,sr3,sr4,sr5,sr6,sr7}=0;
        start = 1; @(posedge clk); start = 0;
        wait_done;

        check_bin(fr0, 0, 0, 0);
        check_bin(fr1, 0, 0, 1);
        check_bin(fr7, 0, 0, 7);

        if (fail == 0) begin
            $display("=== ALL TESTS PASSED ===");
        end else begin
            $display("=== %0d FAILURES ===", fail);
        end
        $finish;
    end
endmodule
