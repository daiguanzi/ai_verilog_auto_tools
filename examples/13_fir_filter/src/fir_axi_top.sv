/* verilator lint_off WIDTHTRUNC */
/* verilator lint_off WIDTHEXPAND */
/* verilator lint_off UNUSEDSIGNAL */

module fir_axi_top (
    input  wire        clk,
    input  wire        rst_n,

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

    input  wire [6:0]  s_axil_araddr,
    input  wire        s_axil_arvalid,
    output wire        s_axil_arready,
    output wire [31:0] s_axil_rdata,
    output wire [1:0]  s_axil_rresp,
    output wire        s_axil_rvalid,
    input  wire        s_axil_rready
);

    localparam TAPS = 8;
    localparam DW   = 16;
    localparam CTRL_IDX   = TAPS * 2;
    localparam RESULT_IDX = TAPS * 2 + 1;

    reg [31:0] regs [0:31];
    reg bvalid_q, rvalid_q;
    reg [31:0] rdata_q;
    reg start_req;
    reg done_q;
    reg state;
    reg [4:0] tap_idx;
    reg signed [31:0] acc;

    wire [4:0] waddr_idx = s_axil_awaddr[6:2];
    wire [4:0] raddr_idx = s_axil_araddr[6:2];

    assign s_axil_awready = 1'b1;
    assign s_axil_wready  = 1'b1;
    assign s_axil_arready = 1'b1;
    assign s_axil_bvalid = bvalid_q;
    assign s_axil_bresp  = 2'b00;
    assign s_axil_rdata  = rdata_q;
    assign s_axil_rvalid = rvalid_q;
    assign s_axil_rresp  = 2'b00;

    // AXI write response
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            bvalid_q <= 1'b0;
        else if (s_axil_awvalid && s_axil_wvalid)
            bvalid_q <= 1'b1;
        else if (s_axil_bready)
            bvalid_q <= 1'b0;
    end

    // Register file + start auto-clear
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < 32; i++) regs[i] <= 32'd0;
            start_req <= 1'b0;
        end else begin
            if (s_axil_awvalid && s_axil_wvalid) begin
                if (waddr_idx == CTRL_IDX)
                    start_req <= s_axil_wdata[0];
                else begin
                    for (int i = 0; i < 4; i++)
                        if (s_axil_wstrb[i])
                            regs[waddr_idx][8*i+:8] <= s_axil_wdata[8*i+:8];
                end
            end
            if (state == 1'b1)
                start_req <= 1'b0;
            if (state == 1'b0 && done_q)
                regs[RESULT_IDX] <= acc;
        end
    end

    // Read path
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rdata_q  <= 32'd0;
            rvalid_q <= 1'b0;
        end else begin
            if (s_axil_arvalid && s_axil_arready) begin
                if (raddr_idx == CTRL_IDX)
                    rdata_q <= {31'd0, done_q};
                else
                    rdata_q <= regs[raddr_idx];
                rvalid_q <= 1'b1;
            end else if (s_axil_rready) begin
                rvalid_q <= 1'b0;
            end
        end
    end

    // ============================================================
    //  FIR filter — direct-form serial MAC (no pipeline)
    //  taps: 16 x (16-bit x 16-bit) → 32-bit output
    // ============================================================

    wire signed [DW-1:0] coeff_mux;
    wire signed [DW-1:0] sample_mux;

    assign coeff_mux = regs[tap_idx][DW-1:0];
    assign sample_mux = regs[tap_idx + TAPS][DW-1:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= 1'b0;
            tap_idx <= 5'd0;
            acc <= 32'd0;
            done_q <= 1'b0;
        end else begin
            if (done_q && start_req)
                done_q <= 1'b0;

            case (state)
                1'b0: if (start_req) begin
                    tap_idx <= 5'd0;
                    acc <= 32'd0;
                    state <= 1'b1;
                end

                1'b1: begin
                    acc <= acc + $signed(coeff_mux) * $signed(sample_mux);
                    if (tap_idx == TAPS - 1) begin
                        state <= 1'b0;
                        done_q <= 1'b1;
                    end else begin
                        tap_idx <= tap_idx + 1;
                    end
                end
            endcase
        end
    end

endmodule
