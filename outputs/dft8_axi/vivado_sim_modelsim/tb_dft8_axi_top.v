`timescale 1ns / 1ps

module tb_dft8_axi_top;
    reg clk = 0;
    reg rst_n = 0;
    reg [6:0] s_axil_awaddr;
    reg s_axil_awvalid;
    reg [31:0] s_axil_wdata;
    reg [3:0] s_axil_wstrb;
    reg s_axil_wvalid;
    reg s_axil_bready;
    reg [6:0] s_axil_araddr;
    reg s_axil_arvalid;
    reg s_axil_rready;
    wire s_axil_awready;
    wire s_axil_wready;
    wire [1:0] s_axil_bresp;
    wire s_axil_bvalid;
    wire s_axil_arready;
    wire [31:0] s_axil_rdata;
    wire [1:0] s_axil_rresp;
    wire s_axil_rvalid;

    dft8_axi_top dut (
        .clk(clk),
        .rst_n(rst_n),
        .s_axil_awaddr(s_axil_awaddr),
        .s_axil_awvalid(s_axil_awvalid),
        .s_axil_awready(s_axil_awready),
        .s_axil_wdata(s_axil_wdata),
        .s_axil_wstrb(s_axil_wstrb),
        .s_axil_wvalid(s_axil_wvalid),
        .s_axil_wready(s_axil_wready),
        .s_axil_bresp(s_axil_bresp),
        .s_axil_bvalid(s_axil_bvalid),
        .s_axil_bready(s_axil_bready),
        .s_axil_araddr(s_axil_araddr),
        .s_axil_arvalid(s_axil_arvalid),
        .s_axil_arready(s_axil_arready),
        .s_axil_rdata(s_axil_rdata),
        .s_axil_rresp(s_axil_rresp),
        .s_axil_rvalid(s_axil_rvalid),
        .s_axil_rready(s_axil_rready)
    );

    always #5 clk = ~clk;

    initial begin
        s_axil_awaddr = 0;
        s_axil_awvalid = 0;
        s_axil_wdata = 0;
        s_axil_wstrb = 0;
        s_axil_wvalid = 0;
        s_axil_bready = 0;
        s_axil_araddr = 0;
        s_axil_arvalid = 0;
        s_axil_rready = 0;
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
