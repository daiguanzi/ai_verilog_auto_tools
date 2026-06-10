module fifo #(
    parameter int DATA_WIDTH = 8,
    parameter int DEPTH      = 16
) (
    input  logic                     clk,
    input  logic                     rst_n,
    input  logic                     wr_en,
    input  logic                     rd_en,
    input  logic [DATA_WIDTH-1:0]    data_in,
    output logic [DATA_WIDTH-1:0]    data_out,
    output logic                     full,
    output logic                     empty
);
    localparam int ADDR_WIDTH = $clog2(DEPTH);

    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    logic [ADDR_WIDTH-1:0] wr_ptr_q, wr_ptr_d;
    logic [ADDR_WIDTH-1:0] rd_ptr_q, rd_ptr_d;
    int                    count_q, count_d;

    logic [DATA_WIDTH-1:0] data_out_q, data_out_d;
    logic                  full_q, full_d;
    logic                  empty_q, empty_d;

    assign data_out = data_out_q;
    assign full     = full_q;
    assign empty    = empty_q;

    always_comb begin
        wr_ptr_d    = wr_ptr_q;
        rd_ptr_d    = rd_ptr_q;
        count_d     = count_q;
        data_out_d  = data_out_q;
        full_d      = full_q;
        empty_d     = empty_q;

        if (wr_en && !full_q) begin
            wr_ptr_d = wr_ptr_q + 1'b1;
            count_d  = count_q + 1;
        end

        if (rd_en && !empty_q) begin
            rd_ptr_d    = rd_ptr_q + 1'b1;
            count_d     = count_d - 1;
            data_out_d  = mem[rd_ptr_q];
        end

        full_d  = (count_d == DEPTH);
        empty_d = (count_d == 0);
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr_q   <= '0;
            rd_ptr_q   <= '0;
            count_q    <= 0;
            data_out_q <= '0;
            full_q     <= 1'b0;
            empty_q    <= 1'b1;
        end else begin
            wr_ptr_q   <= wr_ptr_d;
            rd_ptr_q   <= rd_ptr_d;
            count_q    <= count_d;
            data_out_q <= data_out_d;
            full_q     <= full_d;
            empty_q    <= empty_d;
        end
    end

    always_ff @(posedge clk) begin
        if (wr_en && !full_q)
            mem[wr_ptr_q] <= data_in;
    end

endmodule
