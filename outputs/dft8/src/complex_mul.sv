/* verilator lint_off WIDTHTRUNC */
/* verilator lint_off WIDTHEXPAND */

module complex_mul (
    input  logic [15:0] a_real, a_imag,
    input  logic [15:0] b_real, b_imag,
    output logic [31:0] p_real, p_imag
);
    // (a_r + j*a_i) * (b_r + j*b_i) = (a_r*b_r - a_i*b_i) + j*(a_r*b_i + a_i*b_r)
    wire signed [31:0] ac = $signed(a_real) * $signed(b_real);
    wire signed [31:0] bd = $signed(a_imag) * $signed(b_imag);
    wire signed [31:0] ad = $signed(a_real) * $signed(b_imag);
    wire signed [31:0] bc = $signed(a_imag) * $signed(b_real);

    assign p_real = ac - bd;
    assign p_imag = ad + bc;
endmodule
