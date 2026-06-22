module counter #(
    parameter WIDTH = 4
) (
    input  logic                clk,
    input  logic                rst_n,
    input  logic                enable,
    input  logic                load,
    input  logic                up_down,
    input  logic [WIDTH-1:0]    data_in,
    output logic [WIDTH-1:0]    count,
    output logic                terminal_count
);
    logic [WIDTH-1:0] count_q, count_d;
    logic             tc_q, tc_d;

    assign count          = count_q;
    assign terminal_count = tc_q;

    always_comb begin
        count_d = count_q;

        if (load)
            count_d = data_in;
        else if (enable) begin
            if (up_down)
                count_d = count_q - 1'b1;
            else
                count_d = count_q + 1'b1;
        end

        tc_d = up_down ? (count_d == '0) : (count_d == {WIDTH{1'b1}});
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count_q <= '0;
            tc_q    <= 1'b0;
        end else begin
            count_q <= count_d;
            tc_q    <= tc_d;
        end
    end

endmodule
