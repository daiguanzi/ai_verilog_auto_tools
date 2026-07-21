/* verilator lint_off UNUSEDSIGNAL */
module axis_top (
    input  wire        clk,
    input  wire        rst_n,

    // AXI-Stream slave (input)
    input  wire [31:0] s_axis_tdata,
    input  wire        s_axis_tvalid,
    output wire        s_axis_tready,
    input  wire        s_axis_tlast,

    // AXI-Lite write (unused, present for bus binding)
    input  wire [6:0]  s_axil_awaddr,
    input  wire        s_axil_awvalid,
    output wire        s_axil_awready,
    input  wire [31:0] s_axil_wdata,
    input  wire [3:0]  s_axil_wstrb,
    input  wire        s_axil_wvalid,
    output wire        s_axil_wready,
    output wire [1:0]  s_axil_bresp,
    output wire        s_axil_bvalid,
    input  wire        s_axil_bready,

    // AXI-Lite read
    input  wire [6:0]  s_axil_araddr,
    input  wire        s_axil_arvalid,
    output wire        s_axil_arready,
    output wire [31:0] s_axil_rdata,
    output wire [1:0]  s_axil_rresp,
    output wire        s_axil_rvalid,
    input  wire        s_axil_rready
);

    assign s_axis_tready = 1'b1;
    assign s_axil_awready = 1'b1;
    assign s_axil_wready  = 1'b1;
    assign s_axil_bvalid  = 1'b0;
    assign s_axil_bresp   = 2'b00;

    reg [31:0] regs [0:3];
    reg [1:0]  idx;
    reg [31:0] rdata_q;
    reg rvalid_q;

    wire [4:0] raddr_idx = s_axil_araddr[6:2];

    assign s_axil_arready = 1'b1;
    assign s_axil_rdata   = rdata_q;
    assign s_axil_rvalid  = rvalid_q;
    assign s_axil_rresp   = 2'b00;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            idx <= 0;
            for (int i = 0; i < 4; i++) regs[i] <= 0;
        end else if (s_axis_tvalid) begin
            regs[idx] <= s_axis_tdata;
            idx <= s_axis_tlast ? 2'd0 : idx + 1;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rdata_q <= 0;
            rvalid_q <= 0;
        end else begin
            if (s_axil_arvalid && s_axil_arready) begin
                rdata_q <= regs[raddr_idx[1:0]];
                rvalid_q <= 1'b1;
            end else if (s_axil_rready) begin
                rvalid_q <= 1'b0;
            end
        end
    end

endmodule
