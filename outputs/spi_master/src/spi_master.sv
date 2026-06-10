module spi_master #(
    parameter int CLK_FREQ = 1_000_000,
    parameter int SPI_FREQ = 250_000
) (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [7:0]  data_in,
    input  logic        send,
    input  logic        miso,
    output logic        sck,
    output logic        mosi,
    output logic        cs_n,
    output logic [7:0]  data_out,
    output logic        busy,
    output logic        done
);
    localparam int HALF_PERIOD = (CLK_FREQ / SPI_FREQ) / 2;

    typedef enum logic [2:0] {
        S_IDLE      = 3'b000,
        S_LEAD      = 3'b001,
        S_SCK_HIGH  = 3'b010,
        S_SCK_LOW   = 3'b011,
        S_TRAIL     = 3'b100,
        S_DONE      = 3'b101
    } state_t;

    state_t state_q, state_d;
    int     tick_cnt_q, tick_cnt_d;
    int     bit_idx_q, bit_idx_d;
    logic [7:0] tx_data_q, tx_data_d;
    logic [7:0] rx_data_q, rx_data_d;

    logic sck_q, sck_d;
    logic mosi_q, mosi_d;
    logic cs_n_q, cs_n_d;
    logic busy_q, busy_d;
    logic done_q, done_d;

    assign sck      = sck_q;
    assign mosi     = mosi_q;
    assign cs_n     = cs_n_q;
    assign data_out = rx_data_q;
    assign busy     = busy_q;
    assign done     = done_q;

    always_comb begin
        state_d    = state_q;
        tick_cnt_d = tick_cnt_q;
        bit_idx_d  = bit_idx_q;
        tx_data_d  = tx_data_q;
        rx_data_d  = rx_data_q;
        sck_d      = sck_q;
        mosi_d     = mosi_q;
        cs_n_d     = cs_n_q;
        busy_d     = busy_q;
        done_d     = 1'b0;

        case (state_q)
            S_IDLE: begin
                sck_d  = 1'b0;
                cs_n_d = 1'b1;
                busy_d = 1'b0;
                tick_cnt_d = 0;
                if (send) begin
                    tx_data_d = data_in;
                    rx_data_d = 8'd0;
                    bit_idx_d = 7;
                    state_d   = S_LEAD;
                end
            end

            S_LEAD: begin
                sck_d  = 1'b0;
                cs_n_d = 1'b0;
                busy_d = 1'b1;
                mosi_d = tx_data_q[7];
                if (tick_cnt_q >= HALF_PERIOD - 1) begin
                    tick_cnt_d = 0;
                    state_d    = S_SCK_HIGH;
                end else begin
                    tick_cnt_d = tick_cnt_q + 1;
                end
            end

            S_SCK_HIGH: begin
                sck_d  = 1'b1;
                cs_n_d = 1'b0;
                busy_d = 1'b1;
                if (tick_cnt_q >= HALF_PERIOD - 1) begin
                    tick_cnt_d = 0;
                    rx_data_d[bit_idx_q] = miso;
                    if (bit_idx_q == 0) begin
                        state_d = S_TRAIL;
                    end else begin
                        bit_idx_d = bit_idx_q - 1;
                        state_d   = S_SCK_LOW;
                    end
                end else begin
                    tick_cnt_d = tick_cnt_q + 1;
                end
            end

            S_SCK_LOW: begin
                sck_d  = 1'b0;
                cs_n_d = 1'b0;
                busy_d = 1'b1;
                mosi_d = tx_data_q[bit_idx_q];
                if (tick_cnt_q >= HALF_PERIOD - 1) begin
                    tick_cnt_d = 0;
                    state_d    = S_SCK_HIGH;
                end else begin
                    tick_cnt_d = tick_cnt_q + 1;
                end
            end

            S_TRAIL: begin
                sck_d  = 1'b0;
                cs_n_d = 1'b1;
                busy_d = 1'b1;
                if (tick_cnt_q >= HALF_PERIOD - 1) begin
                    tick_cnt_d = 0;
                    state_d    = S_DONE;
                end else begin
                    tick_cnt_d = tick_cnt_q + 1;
                end
            end

            S_DONE: begin
                sck_d  = 1'b0;
                cs_n_d = 1'b1;
                busy_d = 1'b0;
                done_d = 1'b1;
                state_d = S_IDLE;
            end

            default: state_d = S_IDLE;
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state_q    <= S_IDLE;
            tick_cnt_q <= 0;
            bit_idx_q  <= 0;
            tx_data_q  <= 8'd0;
            rx_data_q  <= 8'd0;
            sck_q      <= 1'b0;
            mosi_q     <= 1'b0;
            cs_n_q     <= 1'b1;
            busy_q     <= 1'b0;
            done_q     <= 1'b0;
        end else begin
            state_q    <= state_d;
            tick_cnt_q <= tick_cnt_d;
            bit_idx_q  <= bit_idx_d;
            tx_data_q  <= tx_data_d;
            rx_data_q  <= rx_data_d;
            sck_q      <= sck_d;
            mosi_q     <= mosi_d;
            cs_n_q     <= cs_n_d;
            busy_q     <= busy_d;
            done_q     <= done_d;
        end
    end

endmodule
