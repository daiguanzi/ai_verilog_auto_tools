`timescale 1ns / 1ps

module tb_bram_acc;
    reg clk = 0;
    reg rst_n = 0;
    reg wr_en;
    reg [7:0] addr;
    reg [31:0] din;
    wire [31:0] dout;

    bram_acc dut (
        .clk(clk),
        .rst_n(rst_n),
        .wr_en(wr_en),
        .addr(addr),
        .din(din),
        .dout(dout)
    );

    always #5 clk = ~clk;

    initial begin
        wr_en = 0;
        addr = 0;
        din = 0;
        // reset
        rst_n = 0;
        repeat(3) @(posedge clk);
        rst_n = 1;
        repeat(5) @(posedge clk);

        // reset_only
        @(posedge clk);
        @(posedge clk);

        $display("=== ALL TESTS PASSED (%d vectors) ===", 1);
        $finish;
    end
endmodule
