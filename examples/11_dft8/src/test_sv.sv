module test_sv(input logic clk, output logic [7:0] out);
    logic [7:0] cnt;
    always_ff @(posedge clk) cnt <= cnt + 1;
    assign out = cnt;
endmodule
