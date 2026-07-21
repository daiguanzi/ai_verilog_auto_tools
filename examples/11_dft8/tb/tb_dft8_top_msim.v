`timescale 1ns / 1ps

module tb_dft8_top;
    reg clk = 0;
    reg rst_n = 0;
    reg start;
    reg [15:0] sr0;
    reg [15:0] si0;
    reg [15:0] sr1;
    reg [15:0] si1;
    reg [15:0] sr2;
    reg [15:0] si2;
    reg [15:0] sr3;
    reg [15:0] si3;
    reg [15:0] sr4;
    reg [15:0] si4;
    reg [15:0] sr5;
    reg [15:0] si5;
    reg [15:0] sr6;
    reg [15:0] si6;
    reg [15:0] sr7;
    reg [15:0] si7;
    wire [15:0] fr0;
    wire [15:0] fi0;
    wire [15:0] fr1;
    wire [15:0] fi1;
    wire [15:0] fr2;
    wire [15:0] fi2;
    wire [15:0] fr3;
    wire [15:0] fi3;
    wire [15:0] fr4;
    wire [15:0] fi4;
    wire [15:0] fr5;
    wire [15:0] fi5;
    wire [15:0] fr6;
    wire [15:0] fi6;
    wire [15:0] fr7;
    wire [15:0] fi7;
    wire done;

    dft8_top dut (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .sr0(sr0),
        .si0(si0),
        .sr1(sr1),
        .si1(si1),
        .sr2(sr2),
        .si2(si2),
        .sr3(sr3),
        .si3(si3),
        .sr4(sr4),
        .si4(si4),
        .sr5(sr5),
        .si5(si5),
        .sr6(sr6),
        .si6(si6),
        .sr7(sr7),
        .si7(si7),
        .fr0(fr0),
        .fi0(fi0),
        .fr1(fr1),
        .fi1(fi1),
        .fr2(fr2),
        .fi2(fi2),
        .fr3(fr3),
        .fi3(fi3),
        .fr4(fr4),
        .fi4(fi4),
        .fr5(fr5),
        .fi5(fi5),
        .fr6(fr6),
        .fi6(fi6),
        .fr7(fr7),
        .fi7(fi7),
        .done(done)
    );

    always #5 clk = ~clk;

    initial begin
        start = 0;
        sr0 = 0;
        si0 = 0;
        sr1 = 0;
        si1 = 0;
        sr2 = 0;
        si2 = 0;
        sr3 = 0;
        si3 = 0;
        sr4 = 0;
        si4 = 0;
        sr5 = 0;
        si5 = 0;
        sr6 = 0;
        si6 = 0;
        sr7 = 0;
        si7 = 0;
        // reset
        rst_n = 0;
        repeat(3) @(posedge clk);
        rst_n = 1;
        repeat(5) @(posedge clk);

        // DC input
        sr0 = 16'd3277;
        si0 = 16'd0;
        sr1 = 16'd3277;
        si1 = 16'd0;
        sr2 = 16'd3277;
        si2 = 16'd0;
        sr3 = 16'd3277;
        si3 = 16'd0;
        sr4 = 16'd3277;
        si4 = 16'd0;
        sr5 = 16'd3277;
        si5 = 16'd0;
        sr6 = 16'd3277;
        si6 = 16'd0;
        sr7 = 16'd3277;
        si7 = 16'd0;
        @(posedge clk);
        @(posedge clk);
        if (fr0 !== 26215) begin
            $display("FAIL [DC input]: fr0 expected %d, got %d", 26215, fr0);
            $stop;
        end
        if (fr1 !== 0) begin
            $display("FAIL [DC input]: fr1 expected %d, got %d", 0, fr1);
            $stop;
        end
        if (fi1 !== 0) begin
            $display("FAIL [DC input]: fi1 expected %d, got %d", 0, fi1);
            $stop;
        end
        if (fr2 !== 0) begin
            $display("FAIL [DC input]: fr2 expected %d, got %d", 0, fr2);
            $stop;
        end
        if (fi2 !== 0) begin
            $display("FAIL [DC input]: fi2 expected %d, got %d", 0, fi2);
            $stop;
        end
        if (fr3 !== 0) begin
            $display("FAIL [DC input]: fr3 expected %d, got %d", 0, fr3);
            $stop;
        end
        if (fi3 !== 0) begin
            $display("FAIL [DC input]: fi3 expected %d, got %d", 0, fi3);
            $stop;
        end
        if (fr4 !== 0) begin
            $display("FAIL [DC input]: fr4 expected %d, got %d", 0, fr4);
            $stop;
        end
        if (fi4 !== 0) begin
            $display("FAIL [DC input]: fi4 expected %d, got %d", 0, fi4);
            $stop;
        end
        if (fr5 !== 0) begin
            $display("FAIL [DC input]: fr5 expected %d, got %d", 0, fr5);
            $stop;
        end
        if (fi5 !== 0) begin
            $display("FAIL [DC input]: fi5 expected %d, got %d", 0, fi5);
            $stop;
        end
        if (fr6 !== 0) begin
            $display("FAIL [DC input]: fr6 expected %d, got %d", 0, fr6);
            $stop;
        end
        if (fi6 !== 0) begin
            $display("FAIL [DC input]: fi6 expected %d, got %d", 0, fi6);
            $stop;
        end
        if (fr7 !== 0) begin
            $display("FAIL [DC input]: fr7 expected %d, got %d", 0, fr7);
            $stop;
        end
        if (fi7 !== 0) begin
            $display("FAIL [DC input]: fi7 expected %d, got %d", 0, fi7);
            $stop;
        end
        if (fi0 !== 0) begin
            $display("FAIL [DC input]: fi0 expected %d, got %d", 0, fi0);
            $stop;
        end

        // all zeros
        sr0 = 16'd0;
        si0 = 16'd0;
        sr1 = 16'd0;
        si1 = 16'd0;
        sr2 = 16'd0;
        si2 = 16'd0;
        sr3 = 16'd0;
        si3 = 16'd0;
        sr4 = 16'd0;
        si4 = 16'd0;
        sr5 = 16'd0;
        si5 = 16'd0;
        sr6 = 16'd0;
        si6 = 16'd0;
        sr7 = 16'd0;
        si7 = 16'd0;
        @(posedge clk);
        @(posedge clk);
        if (fr0 !== 0) begin
            $display("FAIL [all zeros]: fr0 expected %d, got %d", 0, fr0);
            $stop;
        end
        if (fi0 !== 0) begin
            $display("FAIL [all zeros]: fi0 expected %d, got %d", 0, fi0);
            $stop;
        end
        if (fr1 !== 0) begin
            $display("FAIL [all zeros]: fr1 expected %d, got %d", 0, fr1);
            $stop;
        end
        if (fi1 !== 0) begin
            $display("FAIL [all zeros]: fi1 expected %d, got %d", 0, fi1);
            $stop;
        end
        if (fr2 !== 0) begin
            $display("FAIL [all zeros]: fr2 expected %d, got %d", 0, fr2);
            $stop;
        end
        if (fi2 !== 0) begin
            $display("FAIL [all zeros]: fi2 expected %d, got %d", 0, fi2);
            $stop;
        end
        if (fr3 !== 0) begin
            $display("FAIL [all zeros]: fr3 expected %d, got %d", 0, fr3);
            $stop;
        end
        if (fi3 !== 0) begin
            $display("FAIL [all zeros]: fi3 expected %d, got %d", 0, fi3);
            $stop;
        end
        if (fr4 !== 0) begin
            $display("FAIL [all zeros]: fr4 expected %d, got %d", 0, fr4);
            $stop;
        end
        if (fi4 !== 0) begin
            $display("FAIL [all zeros]: fi4 expected %d, got %d", 0, fi4);
            $stop;
        end
        if (fr5 !== 0) begin
            $display("FAIL [all zeros]: fr5 expected %d, got %d", 0, fr5);
            $stop;
        end
        if (fi5 !== 0) begin
            $display("FAIL [all zeros]: fi5 expected %d, got %d", 0, fi5);
            $stop;
        end
        if (fr6 !== 0) begin
            $display("FAIL [all zeros]: fr6 expected %d, got %d", 0, fr6);
            $stop;
        end
        if (fi6 !== 0) begin
            $display("FAIL [all zeros]: fi6 expected %d, got %d", 0, fi6);
            $stop;
        end
        if (fr7 !== 0) begin
            $display("FAIL [all zeros]: fr7 expected %d, got %d", 0, fr7);
            $stop;
        end
        if (fi7 !== 0) begin
            $display("FAIL [all zeros]: fi7 expected %d, got %d", 0, fi7);
            $stop;
        end

        $display("=== ALL TESTS PASSED (%d vectors) ===", 2);
        $finish;
    end
endmodule
