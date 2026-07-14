// ===================================================================
//  ip_models/fifo — Xilinx fifo_generator compatible FIFO stub model
//
//  Covers the following modes used in the user's reference projects:
//    - Common-clock FIFO (acc_fifo, dft_fifo)
//    - Independent-clock FIFO (ad_fifo)
//    - Asymmetric port widths (all three instances)
//
//  Parameters modelled on fifo_generator v13.2 key options.
// ===================================================================
/* verilator lint_off WIDTHTRUNC */
/* verilator lint_off WIDTHEXPAND */

module ip_fifo #(
    parameter int WRITE_WIDTH  = 32,
    parameter int WRITE_DEPTH  = 16,
    parameter int READ_WIDTH   = 32,
    parameter int READ_DEPTH   = 16,
    parameter int MODE         = 0,  // 0=common_clock, 1=independent_clocks
    parameter int USE_DATA_COUNT = 0
) (
    // ---- Write port ----
    input  logic                      wr_clk,
    input  logic                      wr_rst_n,
    input  logic                      wr_en,
    input  logic [WRITE_WIDTH-1:0]    din,
    output logic                      full,
    output logic [WRITE_DEPTH:0]      wr_data_count,

    // ---- Read port ----
    input  logic                      rd_clk,
    input  logic                      rd_rst_n,
    input  logic                      rd_en,
    output logic [READ_WIDTH-1:0]     dout,
    output logic                      empty,
    output logic [READ_DEPTH:0]       rd_data_count
);
    // compute GCD of widths for asymmetric port handling
    function automatic int calc_gcd(int a, int b);
        while (b != 0) begin
            int t = b;
            b = a % b;
            a = t;
        end
        return a;
    endfunction

    localparam int UNIT_WIDTH   = calc_gcd(WRITE_WIDTH, READ_WIDTH);
    localparam int WRITE_UNITS  = WRITE_WIDTH / UNIT_WIDTH;
    localparam int READ_UNITS   = READ_WIDTH  / UNIT_WIDTH;
    localparam int MEM_DEPTH    = WRITE_DEPTH * WRITE_UNITS;
    localparam int ADDR_WIDTH   = $clog2(MEM_DEPTH);
    localparam int COUNT_WIDTH  = ADDR_WIDTH + 1;

    localparam [COUNT_WIDTH-1:0] MEM_SIZED   = MEM_DEPTH;
    localparam [COUNT_WIDTH-1:0] WR_UNITS_SZ = WRITE_UNITS;
    localparam [COUNT_WIDTH-1:0] RD_UNITS_SZ = READ_UNITS;

    logic [UNIT_WIDTH-1:0] mem [0:MEM_DEPTH-1];
    logic [ADDR_WIDTH:0]   wr_ptr_q, wr_ptr_d;
    logic [ADDR_WIDTH:0]   rd_ptr_q, rd_ptr_d;
    logic [COUNT_WIDTH-1:0] count_q, count_d;

    logic [READ_WIDTH-1:0] dout_q, dout_d;

    // simple dual-clock FIFO with read-side output register
    localparam int USE_INDEP_CLK = (MODE == 1) ? 1 : 0;

    assign dout    = dout_q;
    assign empty   = (count_q == 0);
    assign full    = (count_q >= MEM_DEPTH);
    assign wr_data_count = count_q;
    assign rd_data_count = count_q;

    wire write_clk  = USE_INDEP_CLK ? wr_clk : rd_clk;  // write side uses wr_clk in indep mode
    wire read_clk   = rd_clk;
    wire write_rst  = USE_INDEP_CLK ? wr_rst_n : rd_rst_n;
    wire read_rst   = rd_rst_n;

    // ================================================================
    //  Combinational next-state logic
    // ================================================================
    always_comb begin
        wr_ptr_d  = wr_ptr_q;
        rd_ptr_d  = rd_ptr_q;
        count_d   = count_q;
        dout_d    = dout_q;

        // write
        if (wr_en && (count_q < MEM_SIZED)) begin
            wr_ptr_d = wr_ptr_q + WR_UNITS_SZ;
            count_d  = count_q + WR_UNITS_SZ;
        end

        // read
        if (rd_en && (count_q >= RD_UNITS_SZ)) begin
            count_d  = count_d - RD_UNITS_SZ;
            rd_ptr_d = rd_ptr_q + RD_UNITS_SZ;
        end

        // assemble read data from memory (only when valid read)
        for (int i = 0; i < READ_UNITS; i++) begin
            dout_d[i*UNIT_WIDTH +: UNIT_WIDTH] = (rd_en && (count_q >= RD_UNITS_SZ))
                ? mem[(rd_ptr_q + i) % MEM_DEPTH]
                : dout_q[i*UNIT_WIDTH +: UNIT_WIDTH];
        end
    end

    // ================================================================
    //  Registers (write side)
    // ================================================================
    always_ff @(posedge write_clk or negedge write_rst) begin
        if (!write_rst) begin
            wr_ptr_q <= '0;
        end else begin
            wr_ptr_q <= wr_ptr_d;
        end
    end

    // ================================================================
    //  Registers (read side)
    // ================================================================
    always_ff @(posedge read_clk or negedge read_rst) begin
        if (!read_rst) begin
            rd_ptr_q <= '0;
            count_q  <= 0;
            dout_q   <= '0;
        end else begin
            rd_ptr_q <= rd_ptr_d;
            count_q  <= count_d;
            dout_q   <= dout_d;
        end
    end

    // ================================================================
    //  Write to memory (uses wr_clk)
    // ================================================================
    always_ff @(posedge write_clk) begin
        if (wr_en && (count_q < MEM_SIZED)) begin
            for (int i = 0; i < WRITE_UNITS; i++) begin
                mem[(wr_ptr_q + i) % MEM_DEPTH] <= din[i*UNIT_WIDTH +: UNIT_WIDTH];
            end
        end
    end

endmodule
