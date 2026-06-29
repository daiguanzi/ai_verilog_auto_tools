module multiplier #(
    parameter int WIDTH = 8
) (
    input  logic [WIDTH-1:0]    a,
    input  logic [WIDTH-1:0]    b,
    output logic [2*WIDTH-1:0]  prod
);
    assign prod = a * b;
endmodule
