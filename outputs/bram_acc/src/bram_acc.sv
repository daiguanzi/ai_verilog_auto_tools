module bram_acc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        wr_en,
    input  wire [7:0]  addr,
    input  wire [31:0] din,
    output wire [31:0] dout
);

    wire ena, enb;
    wire [3:0] wea;
    wire [31:0] douta;

    assign ena = 1'b1;
    assign enb = 1'b1;
    assign wea = wr_en ? 4'hF : 4'h0;

    ip_bram #(.WIDTH_A(32), .DEPTH_A(256), .WIDTH_B(32), .DEPTH_B(256), .MODE(0), .LATENCY(1))
    u_bram (.clka(clk), .ena(ena), .wea(wea), .addra(addr), .dina(din), .douta(douta),
            .clkb(clk), .enb(enb), .web(4'h0), .addrb(addr), .dinb(32'd0), .doutb(dout));

endmodule
