`include "defs.svh"

module widthmod #(
    parameter int WIDTH = 8
) (
    input  logic             clk,
    output logic [WIDTH-1:0] maxval,
    output logic [7:0]       tag
);
    assign maxval = '1;

`ifdef EXTRA
    assign tag = `MAGIC;
`else
    assign tag = 8'h00;
`endif
endmodule
