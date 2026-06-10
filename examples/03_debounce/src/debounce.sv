module debounce #(
    parameter int CLK_FREQ_HZ   = 100_000,
    parameter int DEBOUNCE_MS   = 1
) (
    input  logic clk,
    input  logic rst_n,
    input  logic button_in,
    output logic button_out
);
    localparam int MAX_COUNT = (CLK_FREQ_HZ / 1000) * DEBOUNCE_MS;

    typedef enum logic [1:0] {
        S_IDLE          = 2'b00,
        S_COUNT         = 2'b01,
        S_PULSE         = 2'b10,
        S_WAIT_RELEASE  = 2'b11
    } state_t;

    state_t state_q, state_d;
    int      counter_q, counter_d;
    logic    button_out_q, button_out_d;

    assign button_out = button_out_q;

    always_comb begin
        state_d       = state_q;
        counter_d     = counter_q;
        button_out_d  = 1'b0;

        case (state_q)
            S_IDLE: begin
                counter_d = 0;
                if (button_in)
                    state_d = S_COUNT;
            end

            S_COUNT: begin
                if (!button_in) begin
                    counter_d = 0;
                    state_d = S_IDLE;
                end else if (counter_q >= MAX_COUNT - 1) begin
                    counter_d = 0;
                    state_d = S_PULSE;
                end else begin
                    counter_d = counter_q + 1;
                end
            end

            S_PULSE: begin
                button_out_d = 1'b1;
                state_d = S_WAIT_RELEASE;
            end

            S_WAIT_RELEASE: begin
                if (!button_in)
                    state_d = S_IDLE;
            end

            default: state_d = S_IDLE;
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state_q      <= S_IDLE;
            counter_q    <= 0;
            button_out_q <= 1'b0;
        end else begin
            state_q      <= state_d;
            counter_q    <= counter_d;
            button_out_q <= button_out_d;
        end
    end

endmodule
