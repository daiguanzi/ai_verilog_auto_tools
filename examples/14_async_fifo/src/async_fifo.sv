/* verilator lint_off WIDTHTRUNC */
/* verilator lint_off WIDTHEXPAND */
/* verilator lint_off UNUSEDSIGNAL */

module async_fifo #(
    parameter DEPTH = 8,
    parameter DW    = 16
) (
    input  wire             wclk,
    input  wire             wrst_n,
    input  wire             wr_en,
    input  wire [DW-1:0]    din,
    output wire             full,

    input  wire             rclk,
    input  wire             rrst_n,
    input  wire             rd_en,
    output wire [DW-1:0]    dout,
    output wire             empty
);

    localparam AW = $clog2(DEPTH);

    reg [DW-1:0] mem [0:DEPTH-1];

    // Write domain
    reg [AW:0] wptr_bin, wptr_gray;
    reg [AW:0] wptr_gray_next;
    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wptr_bin <= 0;
            wptr_gray <= 0;
        end else if (wr_en && !full) begin
            mem[wptr_bin[AW-1:0]] <= din;
            wptr_bin <= wptr_bin + 1;
            wptr_gray <= wptr_gray_next;
        end
    end

    // Gray code: next = (bin+1) ^ ((bin+1) >> 1)
    wire [AW:0] wbin_next = wptr_bin + 1;
    assign wptr_gray_next = wbin_next ^ (wbin_next >> 1);

    // Read domain
    reg [AW:0] rptr_bin, rptr_gray;
    reg [AW:0] rptr_gray_next;
    reg [DW-1:0] dout_reg;
    assign dout = dout_reg;

    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            rptr_bin <= 0;
            rptr_gray <= 0;
            dout_reg <= 0;
        end else if (rd_en && !empty) begin
            dout_reg <= mem[rptr_bin[AW-1:0]];
            rptr_bin <= rptr_bin + 1;
            rptr_gray <= rptr_gray_next;
        end
    end

    wire [AW:0] rbin_next = rptr_bin + 1;
    assign rptr_gray_next = rbin_next ^ (rbin_next >> 1);

    // CDC synchronizers (2-FF)
    reg [AW:0] wptr_sync1, wptr_sync2;
    reg [AW:0] rptr_sync1, rptr_sync2;

    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            wptr_sync1 <= 0;
            wptr_sync2 <= 0;
        end else begin
            wptr_sync1 <= wptr_gray;
            wptr_sync2 <= wptr_sync1;
        end
    end

    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            rptr_sync1 <= 0;
            rptr_sync2 <= 0;
        end else begin
            rptr_sync1 <= rptr_gray;
            rptr_sync2 <= rptr_sync1;
        end
    end

    // Full detection in write domain (gray comparison)
    // Full when next write gray ptr equals synced read with top 2 bits toggled
    wire full_cond = (wptr_gray_next[AW] != rptr_sync2[AW]) &&
                     (wptr_gray_next[AW-1] != rptr_sync2[AW-1]) &&
                     (wptr_gray_next[AW-2:0] == rptr_sync2[AW-2:0]);
    assign full = full_cond;

    // Empty detection in read domain (gray comparison)
    assign empty = (wptr_sync2 == rptr_gray);

endmodule
