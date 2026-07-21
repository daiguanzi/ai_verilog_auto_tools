/* verilator lint_off WIDTHTRUNC */
/* verilator lint_off WIDTHEXPAND */
/* verilator lint_off UNUSEDSIGNAL */

module dft8_axi_top (
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

    localparam CTRL_IDX = 5'd16;
    localparam OUT_BASE  = 5'd24;

    // ---- AXI register file ----
    reg [31:0] regs [0:31];
    reg bvalid_q, rvalid_q;
    reg [31:0] rdata_q;
    reg start_req;
    reg done_q;

    // ---- DFT8 computation engine signals ----
    reg [1:0]  state;
    reg [2:0]  k_idx, n_idx;
    reg signed [39:0] acc_r, acc_i;

    wire signed [15:0] tw_r0 = 16'h7FFF;
    wire signed [15:0] tw_r1 = 16'h5A82;
    wire signed [15:0] tw_r2 = 16'h0000;
    wire signed [15:0] tw_r3 = 16'hA57E;
    wire signed [15:0] tw_r4 = 16'h8001;
    wire signed [15:0] tw_r5 = 16'hA57E;
    wire signed [15:0] tw_r6 = 16'h0000;
    wire signed [15:0] tw_r7 = 16'h5A82;

    wire signed [15:0] tw_i0 = 16'h0000;
    wire signed [15:0] tw_i1 = 16'hA57E;
    wire signed [15:0] tw_i2 = 16'h8001;
    wire signed [15:0] tw_i3 = 16'hA57E;
    wire signed [15:0] tw_i4 = 16'h0000;
    wire signed [15:0] tw_i5 = 16'h5A82;
    wire signed [15:0] tw_i6 = 16'h7FFF;
    wire signed [15:0] tw_i7 = 16'h5A82;

    wire [2:0] tw = (k_idx * n_idx) & 3'h7;
    wire signed [15:0] cur_tw_r = (tw==0)?tw_r0:(tw==1)?tw_r1:(tw==2)?tw_r2:(tw==3)?tw_r3
                                :(tw==4)?tw_r4:(tw==5)?tw_r5:(tw==6)?tw_r6:tw_r7;
    wire signed [15:0] cur_tw_i = (tw==0)?tw_i0:(tw==1)?tw_i1:(tw==2)?tw_i2:(tw==3)?tw_i3
                                :(tw==4)?tw_i4:(tw==5)?tw_i5:(tw==6)?tw_i6:tw_i7;

    wire signed [15:0] cur_sr = (n_idx==0)?regs[0][15:0] :(n_idx==1)?regs[1][15:0]
                              :(n_idx==2)?regs[2][15:0] :(n_idx==3)?regs[3][15:0]
                              :(n_idx==4)?regs[4][15:0] :(n_idx==5)?regs[5][15:0]
                              :(n_idx==6)?regs[6][15:0] :regs[7][15:0];
    wire signed [15:0] cur_si = (n_idx==0)?$signed(regs[0][31:16]):(n_idx==1)?$signed(regs[1][31:16])
                              :(n_idx==2)?$signed(regs[2][31:16]):(n_idx==3)?$signed(regs[3][31:16])
                              :(n_idx==4)?$signed(regs[4][31:16]):(n_idx==5)?$signed(regs[5][31:16])
                              :(n_idx==6)?$signed(regs[6][31:16]):$signed(regs[7][31:16]);

    wire signed [31:0] ac = cur_sr * cur_tw_r;
    wire signed [31:0] bd = cur_si * cur_tw_i;
    wire signed [31:0] ad = cur_sr * cur_tw_i;
    wire signed [31:0] bc = cur_si * cur_tw_r;
    wire signed [31:0] m_r = ac - bd;
    wire signed [31:0] m_i = ad + bc;

    wire [15:0] dft_out_r = (acc_r + m_r) >>> 15;
    wire [15:0] dft_out_i = (acc_i + m_i) >>> 15;

    wire [4:0] waddr_idx = s_axil_awaddr[6:2];
    wire [4:0] raddr_idx = s_axil_araddr[6:2];

    // ---- AXI handshake ----
    assign s_axil_awready = 1'b1;
    assign s_axil_wready  = 1'b1;
    assign s_axil_arready = 1'b1;

    assign s_axil_bvalid = bvalid_q;
    assign s_axil_bresp  = 2'b00;
    assign s_axil_rdata  = rdata_q;
    assign s_axil_rvalid = rvalid_q;
    assign s_axil_rresp  = 2'b00;

    // ---- AXI Write response ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            bvalid_q <= 1'b0;
        else if (s_axil_awvalid && s_axil_wvalid)
            bvalid_q <= 1'b1;
        else if (s_axil_bready)
            bvalid_q <= 1'b0;
    end

    // ---- Register file + DFT output write + start auto-clear ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < 32; i++) regs[i] <= 32'd0;
            start_req <= 1'b0;
        end else begin
            if (s_axil_awvalid && s_axil_wvalid) begin
                if (waddr_idx == CTRL_IDX) begin
                    start_req <= s_axil_wdata[0];
                end else begin
                    for (int i = 0; i < 4; i++)
                        if (s_axil_wstrb[i])
                            regs[waddr_idx][8*i+:8] <= s_axil_wdata[8*i+:8];
                end
            end
            if (state == 2'd1)
                start_req <= 1'b0;
            if (state == 2'd1 && n_idx == 3'd7)
                regs[OUT_BASE + k_idx] <= {dft_out_i, dft_out_r};
        end
    end

    // ---- AXI Read path ----
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

    // ---- DFT8 FSM ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= 2'd0; k_idx <= 3'd0; n_idx <= 3'd0;
            acc_r <= 40'd0; acc_i <= 40'd0;
            done_q <= 1'b0;
        end else begin
            if (done_q && start_req)
                done_q <= 1'b0;

            case (state)
                2'd0: if (start_req) begin
                    k_idx <= 3'd0; n_idx <= 3'd0;
                    acc_r <= 40'd0; acc_i <= 40'd0;
                    state <= 2'd1;
                end
                2'd1: begin
                    acc_r <= acc_r + m_r;
                    acc_i <= acc_i + m_i;
                    if (n_idx == 3'd7) begin
                        acc_r <= 40'd0;
                        acc_i <= 40'd0;
                        n_idx <= 3'd0;
                        if (k_idx == 3'd7) begin
                            state <= 2'd0;
                            done_q <= 1'b1;
                        end else begin
                            k_idx <= k_idx + 3'd1;
                        end
                    end else begin
                        n_idx <= n_idx + 3'd1;
                    end
                end
                default: state <= 2'd0;
            endcase
        end
    end

endmodule
