module vending_machine (
    input  logic        clk,
    input  logic        rst_n,

    input  logic        coin_05,
    input  logic        coin_1,
    input  logic        coin_2,
    input  logic        cancel,

    output logic [4:0]  amount,
    output logic        dispense,
    output logic [4:0]  change,
    output logic        change_valid
);
    typedef enum logic [1:0] {
        S_ACCUMULATE = 2'b00,
        S_DISPENSE   = 2'b01,
        S_REFUND     = 2'b10
    } state_t;

    state_t state_q, state_d;
    logic [4:0] amount_q, amount_d;
    logic       dispense_q, dispense_d;
    logic [4:0] change_q, change_d;
    logic       change_valid_q, change_valid_d;

    assign dispense     = dispense_q;
    assign change       = change_q;
    assign change_valid = change_valid_q;
    assign amount       = amount_q;

    always_comb begin
        state_d          = state_q;
        amount_d         = amount_q;
        dispense_d       = 1'b0;
        change_d         = 5'd0;
        change_valid_d   = 1'b0;

        case (state_q)
            S_ACCUMULATE: begin
                if (coin_05) amount_d = amount_d + 5'd5;
                if (coin_1)  amount_d = amount_d + 5'd10;
                if (coin_2)  amount_d = amount_d + 5'd20;

                if (amount_d >= 5'd15) begin
                    dispense_d     = 1'b1;
                    change_d       = amount_d - 5'd15;
                    if (change_d > 0) change_valid_d = 1'b1;
                    amount_d       = 5'd0;
                    state_d        = S_DISPENSE;
                end else if (cancel && amount_d > 0) begin
                    change_d       = amount_d;
                    change_valid_d = 1'b1;
                    amount_d       = 5'd0;
                    state_d        = S_REFUND;
                end
            end

            S_DISPENSE: begin
                amount_d  = 5'd0;
                state_d   = S_ACCUMULATE;
            end

            S_REFUND: begin
                amount_d  = 5'd0;
                state_d   = S_ACCUMULATE;
            end

            default: state_d = S_ACCUMULATE;
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state_q        <= S_ACCUMULATE;
            amount_q       <= 5'd0;
            dispense_q     <= 1'b0;
            change_q       <= 5'd0;
            change_valid_q <= 1'b0;
        end else begin
            state_q        <= state_d;
            amount_q       <= amount_d;
            dispense_q     <= dispense_d;
            change_q       <= change_d;
            change_valid_q <= change_valid_d;
        end
    end

endmodule
