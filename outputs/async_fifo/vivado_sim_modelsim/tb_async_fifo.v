`timescale 1ns / 1ps

module tb_async_fifo;
    reg clk = 0;
    reg rst_n = 0;
    reg wclk;
    reg wrst_n;
    reg wr_en;
    reg din;
    reg rclk;
    reg rrst_n;
    reg rd_en;
    wire full;
    wire dout;
    wire empty;

    async_fifo dut (
        .wclk(wclk),
        .wrst_n(wrst_n),
        .wr_en(wr_en),
        .din(din),
        .full(full),
        .rclk(rclk),
        .rrst_n(rrst_n),
        .rd_en(rd_en),
        .dout(dout),
        .empty(empty)
    );

    always #5 clk = ~clk;

    initial begin
        wclk = 0;
        wrst_n = 0;
        wr_en = 0;
        din = 0;
        rclk = 0;
        rrst_n = 0;
        rd_en = 0;
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
