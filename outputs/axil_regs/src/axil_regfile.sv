module axil_regfile #(
    parameter int NREGS      = 4,
    parameter int ADDR_WIDTH = 8
) (
    input  logic                     clk,
    input  logic                     rst_n,

    input  logic [ADDR_WIDTH-1:0]    s_axil_awaddr,
    input  logic                     s_axil_awvalid,
    output logic                     s_axil_awready,

    input  logic [31:0]              s_axil_wdata,
    input  logic [3:0]               s_axil_wstrb,
    input  logic                     s_axil_wvalid,
    output logic                     s_axil_wready,

    output logic [1:0]               s_axil_bresp,
    output logic                     s_axil_bvalid,
    input  logic                     s_axil_bready,

    input  logic [ADDR_WIDTH-1:0]    s_axil_araddr,
    input  logic                     s_axil_arvalid,
    output logic                     s_axil_arready,

    output logic [31:0]              s_axil_rdata,
    output logic [1:0]               s_axil_rresp,
    output logic                     s_axil_rvalid,
    input  logic                     s_axil_rready
);
    localparam int IDX_BITS = $clog2(NREGS);
    logic [31:0] regs [0:NREGS-1];
    logic bvalid_q, rvalid_q;
    logic [31:0] rdata_q;
    logic [IDX_BITS-1:0] waddr_idx, raddr_idx;

    assign s_axil_awready = 1'b1;
    assign s_axil_wready  = 1'b1;
    assign s_axil_arready = 1'b1;

    assign waddr_idx = s_axil_awaddr[IDX_BITS+1:2];
    assign raddr_idx = s_axil_araddr[IDX_BITS+1:2];

    // write response
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            bvalid_q <= 1'b0;
        else if (s_axil_awvalid && s_axil_wvalid)
            bvalid_q <= 1'b1;
        else if (s_axil_bready)
            bvalid_q <= 1'b0;
    end
    assign s_axil_bvalid = bvalid_q;
    assign s_axil_bresp  = 2'b00;

    // write data
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < NREGS; i++)
                regs[i] <= 32'd0;
        end else if (s_axil_awvalid && s_axil_wvalid) begin
            for (int b = 0; b < 4; b++)
                if (s_axil_wstrb[b])
                    regs[waddr_idx][8*b+:8] <= s_axil_wdata[8*b+:8];
        end
    end

    // read
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rdata_q  <= 32'd0;
            rvalid_q <= 1'b0;
        end else begin
            if (s_axil_arvalid)
                rdata_q <= regs[raddr_idx];
            rvalid_q <= s_axil_arvalid;
        end
    end
    assign s_axil_rdata  = rdata_q;
    assign s_axil_rvalid = rvalid_q;
    assign s_axil_rresp  = 2'b00;
endmodule
