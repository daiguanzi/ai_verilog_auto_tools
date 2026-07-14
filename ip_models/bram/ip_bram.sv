module ip_bram #(
    parameter int           WIDTH_A       = 32,
    parameter int           DEPTH_A       = 512,
    parameter int           ADDR_WIDTH_A = $clog2(DEPTH_A),
    parameter int           WIDTH_B       = 32,
    parameter int           DEPTH_B       = 512,
    parameter int           ADDR_WIDTH_B = $clog2(DEPTH_B),
    parameter int           MODE          = 0,   // 0=SDP, 1=SP_RAM, 2=ROM
    parameter int           LATENCY       = 1,
    parameter               INIT_EN       = 0,
    parameter [WIDTH_A-1:0] INIT_VALUE    = '0
) (
    input  logic                              clka,
    input  logic                              ena,
    input  logic [(WIDTH_A/8)-1:0]            wea,
    input  logic [ADDR_WIDTH_A-1:0]           addra,
    input  logic [WIDTH_A-1:0]                dina,
    output logic [WIDTH_A-1:0]                douta,

    input  logic                              clkb,
    input  logic                              enb,
    input  logic [(WIDTH_B/8)-1:0]            web,
    input  logic [ADDR_WIDTH_B-1:0]           addrb,
    input  logic [WIDTH_B-1:0]                dinb,
    output logic [WIDTH_B-1:0]                doutb
);
    localparam int MEM_DEPTH = (WIDTH_A * DEPTH_A > WIDTH_B * DEPTH_B)
                                ? DEPTH_A : DEPTH_B;
    localparam int MEM_WIDTH = WIDTH_A > WIDTH_B ? WIDTH_A : WIDTH_B;

    logic [MEM_WIDTH-1:0] mem [0:MEM_DEPTH-1];

    // Port B output pipeline (LATENCY stages)
    logic [WIDTH_B-1:0] doutb_s0;
    logic [WIDTH_B-1:0] doutb_s1;
    logic [WIDTH_B-1:0] doutb_s2;

    // Port A output pipeline
    logic [WIDTH_A-1:0] douta_s0;
    logic [WIDTH_A-1:0] douta_s1;
    logic [WIDTH_A-1:0] douta_s2;

    // ================================================================
    //  Memory write (Port A)
    // ================================================================
    generate
        if (MODE != 2) begin : gen_write
            always_ff @(posedge clka) begin
                if (ena) begin
                    for (int b = 0; b < WIDTH_A/8; b++) begin
                        if (wea[b])
                            mem[addra][(b+1)*8-1 -: 8] <= dina[(b+1)*8-1 -: 8];
                    end
                end
            end
        end
    endgenerate

    // ================================================================
    //  Memory read (Port B — primary read side in SDP mode)
    // ================================================================
    wire [WIDTH_B-1:0] raw_doutb;
    assign raw_doutb = mem[addrb];

    always_ff @(posedge clkb) begin
        if (enb) begin
            doutb_s0 <= raw_doutb;
            doutb_s1 <= doutb_s0;
            doutb_s2 <= doutb_s1;
        end
    end

    assign doutb = (LATENCY == 0) ? raw_doutb :
                   (LATENCY == 1) ? doutb_s0 :
                   (LATENCY == 2) ? doutb_s1 : doutb_s2;

    // ================================================================
    //  Memory read (Port A — read side in SP_RAM mode)
    // ================================================================
    wire [WIDTH_A-1:0] raw_douta;
    assign raw_douta = mem[addra];

    always_ff @(posedge clka) begin
        if (ena) begin
            douta_s0 <= raw_douta;
            douta_s1 <= douta_s0;
            douta_s2 <= douta_s1;
        end
    end

    assign douta = (LATENCY == 0) ? raw_douta :
                   (LATENCY == 1) ? douta_s0 :
                   (LATENCY == 2) ? douta_s1 : douta_s2;

    // ================================================================
    //  Initialization
    // ================================================================
    generate
        if (INIT_EN) begin : gen_init
            initial begin
                for (int i = 0; i < MEM_DEPTH; i++)
                    mem[i] = INIT_VALUE;
            end
        end
    endgenerate

endmodule
