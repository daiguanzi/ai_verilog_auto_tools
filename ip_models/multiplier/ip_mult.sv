// ===================================================================
//  ip_models/multiplier — Xilinx mult_gen compatible multiplier stub
// ===================================================================
/* verilator lint_off WIDTHTRUNC */
/* verilator lint_off WIDTHEXPAND */

module ip_mult #(
    parameter int A_WIDTH     = 12,
    parameter int B_WIDTH     = 12,
    parameter int OUT_WIDTH   = 24,
    parameter int IS_SIGNED   = 0,
    parameter int LATENCY     = 1
) (
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic [A_WIDTH-1:0]      a,
    input  logic [B_WIDTH-1:0]      b,
    output logic [OUT_WIDTH-1:0]    p
);
    localparam int FULL_WIDTH = A_WIDTH + B_WIDTH;

    wire signed [FULL_WIDTH-1:0] signed_a = {{(FULL_WIDTH - A_WIDTH){a[A_WIDTH-1]}}, a};
    wire signed [FULL_WIDTH-1:0] signed_b = {{(FULL_WIDTH - B_WIDTH){b[B_WIDTH-1]}}, b};

    wire [FULL_WIDTH-1:0] raw;
    assign raw = IS_SIGNED
        ? signed_a * signed_b
        : a * b;

    logic [OUT_WIDTH-1:0] p_s0, p_s1, p_s2;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            p_s0 <= '0; p_s1 <= '0; p_s2 <= '0;
        end else begin
            p_s0 <= raw[OUT_WIDTH-1:0];
            p_s1 <= p_s0;
            p_s2 <= p_s1;
        end
    end

    assign p = (LATENCY == 0) ? raw[OUT_WIDTH-1:0] :
               (LATENCY == 1) ? p_s0 :
               (LATENCY == 2) ? p_s1 : p_s2;
endmodule
