module uart_tx #(
    parameter int CLK_FREQ  = 1_000_000,
    parameter int BAUD_RATE = 100_000
) (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [7:0]  data_in,
    input  logic        send,
    output logic        tx,
    output logic        busy,
    output logic        done
);
    localparam int BIT_PERIOD = CLK_FREQ / BAUD_RATE;

    typedef enum logic [2:0] {
        S_IDLE  = 3'b000,
        S_START = 3'b001,
        S_DATA  = 3'b010,
        S_STOP  = 3'b011,
        S_DONE  = 3'b100
    } state_t;

    state_t state_q, state_d;
    int     bit_cnt_q, bit_cnt_d;
    int     tick_cnt_q, tick_cnt_d;
    logic [7:0] data_q, data_d;

    logic tx_q, tx_d;
    logic busy_q, busy_d;
    logic done_q, done_d;

    assign tx   = tx_q;
    assign busy = busy_q;
    assign done = done_q;

    always_comb begin
        state_d   = state_q;
        bit_cnt_d = bit_cnt_q;
        tick_cnt_d = tick_cnt_q;
        data_d    = data_q;
        tx_d      = tx_q;
        busy_d    = busy_q;
        done_d    = 1'b0;

        case (state_q)
            S_IDLE: begin
                tx_d   = 1'b1;
                busy_d = 1'b0;
                tick_cnt_d = 0;
                bit_cnt_d  = 0;
                if (send) begin
                    data_d  = data_in;
                    state_d = S_START;
                end
            end

            S_START: begin
                tx_d   = 1'b0;
                busy_d = 1'b1;
                if (tick_cnt_q >= BIT_PERIOD - 1) begin
                    tick_cnt_d = 0;
                    bit_cnt_d  = 0;
                    state_d    = S_DATA;
                end else begin
                    tick_cnt_d = tick_cnt_q + 1;
                end
            end

            S_DATA: begin
                tx_d   = data_q[bit_cnt_q];
                busy_d = 1'b1;
                if (tick_cnt_q >= BIT_PERIOD - 1) begin
                    tick_cnt_d = 0;
                    if (bit_cnt_q >= 7) begin
                        bit_cnt_d = 0;
                        state_d   = S_STOP;
                    end else begin
                        bit_cnt_d = bit_cnt_q + 1;
                    end
                end else begin
                    tick_cnt_d = tick_cnt_q + 1;
                end
            end

            S_STOP: begin
                tx_d   = 1'b1;
                busy_d = 1'b1;
                if (tick_cnt_q >= BIT_PERIOD - 1) begin
                    tick_cnt_d = 0;
                    state_d    = S_DONE;
                end else begin
                    tick_cnt_d = tick_cnt_q + 1;
                end
            end

            S_DONE: begin
                tx_d   = 1'b1;
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
            bit_cnt_q  <= 0;
            tick_cnt_q <= 0;
            data_q     <= 8'd0;
            tx_q       <= 1'b1;
            busy_q     <= 1'b0;
            done_q     <= 1'b0;
        end else begin
            state_q    <= state_d;
            bit_cnt_q  <= bit_cnt_d;
            tick_cnt_q <= tick_cnt_d;
            data_q     <= data_d;
            tx_q       <= tx_d;
            busy_q     <= busy_d;
            done_q     <= done_d;
        end
    end

endmodule
