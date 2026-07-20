`timescale 1ns / 1ps

module tb_adder;
    reg clk = 0;
    reg rst_n = 0;
    reg [7:0] a;
    reg [7:0] b;
    wire [8:0] sum;

    adder dut (
        .clk(clk),
        .rst_n(rst_n),
        .a(a),
        .b(b),
        .sum(sum)
    );

    always #5 clk = ~clk;

    initial begin
        a = 0;
        b = 0;
        // reset
        rst_n = 0;
        repeat(3) @(posedge clk);
        rst_n = 1;
        repeat(5) @(posedge clk);

        // 3+4
        a = 8'd3;
        b = 8'd4;
        @(posedge clk);
        @(posedge clk);
        if (sum !== 7) begin
            $display("FAIL [3+4]: sum expected %d, got %d", 7, sum);
            $stop;
        end

        // 255+1
        a = 8'd255;
        b = 8'd1;
        @(posedge clk);
        @(posedge clk);
        if (sum !== 256) begin
            $display("FAIL [255+1]: sum expected %d, got %d", 256, sum);
            $stop;
        end

        $display("=== ALL TESTS PASSED (%d vectors) ===", 2);
        $finish;
    end
endmodule
