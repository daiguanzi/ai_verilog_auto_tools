module mac_unit #(
    parameter int WIDTH = 8
) (
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    enable,
    input  logic [WIDTH-1:0]        a,
    input  logic [WIDTH-1:0]        b,
    output logic [2*WIDTH-1:0]      accum
);
    logic [2*WIDTH-1:0] prod;
    logic [2*WIDTH-1:0] accum_q, accum_d;

    multiplier #(.WIDTH(WIDTH)) u_mult (
        .a(a),
        .b(b),
        .prod(prod)
    );

    assign accum = accum_q;

    always_comb begin
        accum_d = accum_q;
        if (enable)
            accum_d = accum_q + prod;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            accum_q <= '0;
        else
            accum_q <= accum_d;
    end
endmodule
