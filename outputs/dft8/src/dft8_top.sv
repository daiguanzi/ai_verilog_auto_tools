/* verilator lint_off WIDTHTRUNC */
/* verilator lint_off WIDTHEXPAND */

module dft8_top (
    input  logic        clk, rst_n, start,
    input  logic [15:0] sr0, sr1, sr2, sr3, sr4, sr5, sr6, sr7,
    input  logic [15:0] si0, si1, si2, si3, si4, si5, si6, si7,
    output logic [15:0] fr0, fr1, fr2, fr3, fr4, fr5, fr6, fr7,
    output logic [15:0] fi0, fi1, fi2, fi3, fi4, fi5, fi6, fi7,
    output logic        done
);
    reg signed [15:0] tw_r0,tw_r1,tw_r2,tw_r3,tw_r4,tw_r5,tw_r6,tw_r7;
    reg signed [15:0] tw_i0,tw_i1,tw_i2,tw_i3,tw_i4,tw_i5,tw_i6,tw_i7;
    initial begin
        tw_r0=16'h7FFF;tw_r1=16'h5A82;tw_r2=16'h0000;tw_r3=16'hA57E;
        tw_r4=16'h8001;tw_r5=16'hA57E;tw_r6=16'h0000;tw_r7=16'h5A82;
        tw_i0=16'h0000;tw_i1=16'hA57E;tw_i2=16'h8001;tw_i3=16'hA57E;
        tw_i4=16'h0000;tw_i5=16'h5A82;tw_i6=16'h7FFF;tw_i7=16'h5A82;
    end

    reg [15:0] s_r0,s_r1,s_r2,s_r3,s_r4,s_r5,s_r6,s_r7;
    reg [15:0] s_i0,s_i1,s_i2,s_i3,s_i4,s_i5,s_i6,s_i7;
    reg [2:0]  k_idx, n_idx, state;
    reg signed [39:0] acc_r, acc_i;
    reg        done_q;
    reg [15:0] b0r,b1r,b2r,b3r,b4r,b5r,b6r,b7r;
    reg [15:0] b0i,b1i,b2i,b3i,b4i,b5i,b6i,b7i;

    // mux twiddle factors by tw_idx
    wire [2:0] tw = (k_idx * n_idx) & 3'h7;
    wire signed [15:0] cur_tw_r = (tw==0)?tw_r0:(tw==1)?tw_r1:(tw==2)?tw_r2:(tw==3)?tw_r3
                                :(tw==4)?tw_r4:(tw==5)?tw_r5:(tw==6)?tw_r6:tw_r7;
    wire signed [15:0] cur_tw_i = (tw==0)?tw_i0:(tw==1)?tw_i1:(tw==2)?tw_i2:(tw==3)?tw_i3
                                :(tw==4)?tw_i4:(tw==5)?tw_i5:(tw==6)?tw_i6:tw_i7;
    wire signed [15:0] cur_s_r = (n_idx==0)?s_r0:(n_idx==1)?s_r1:(n_idx==2)?s_r2:(n_idx==3)?s_r3
                               :(n_idx==4)?s_r4:(n_idx==5)?s_r5:(n_idx==6)?s_r6:s_r7;
    wire signed [15:0] cur_s_i = (n_idx==0)?s_i0:(n_idx==1)?s_i1:(n_idx==2)?s_i2:(n_idx==3)?s_i3
                               :(n_idx==4)?s_i4:(n_idx==5)?s_i5:(n_idx==6)?s_i6:s_i7;

    wire signed [31:0] ac = $signed(cur_s_r) * $signed(cur_tw_r);
    wire signed [31:0] bd = $signed(cur_s_i) * $signed(cur_tw_i);
    wire signed [31:0] ad = $signed(cur_s_r) * $signed(cur_tw_i);
    wire signed [31:0] bc = $signed(cur_s_i) * $signed(cur_tw_r);
    wire signed [31:0] m_r = ac - bd;
    wire signed [31:0] m_i = ad + bc;

    assign fr0=b0r;assign fr1=b1r;assign fr2=b2r;assign fr3=b3r;
    assign fr4=b4r;assign fr5=b5r;assign fr6=b6r;assign fr7=b7r;
    assign fi0=b0i;assign fi1=b1i;assign fi2=b2i;assign fi3=b3i;
    assign fi4=b4i;assign fi5=b5i;assign fi6=b6i;assign fi7=b7i;
    assign done = done_q;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state<=0;done_q<=0;k_idx<=0;n_idx<=0;acc_r<=0;acc_i<=0;
            {s_r0,s_r1,s_r2,s_r3,s_r4,s_r5,s_r6,s_r7}<=0;
            {s_i0,s_i1,s_i2,s_i3,s_i4,s_i5,s_i6,s_i7}<=0;
            {b0r,b1r,b2r,b3r,b4r,b5r,b6r,b7r}<=0;
            {b0i,b1i,b2i,b3i,b4i,b5i,b6i,b7i}<=0;
        end else begin
            if (done_q && !start) done_q<=1'b0;
            case (state)
                0: if (start) begin
                    s_r0<=sr0;s_r1<=sr1;s_r2<=sr2;s_r3<=sr3;
                    s_r4<=sr4;s_r5<=sr5;s_r6<=sr6;s_r7<=sr7;
                    s_i0<=si0;s_i1<=si1;s_i2<=si2;s_i3<=si3;
                    s_i4<=si4;s_i5<=si5;s_i6<=si6;s_i7<=si7;
                    k_idx<=0;n_idx<=0;acc_r<=0;acc_i<=0;state<=1;
                end
                1: begin
                    acc_r<=acc_r+m_r; acc_i<=acc_i+m_i;
                    if (n_idx==7) begin
                        case (k_idx)
                            0: begin b0r<=(acc_r+m_r)>>>15; b0i<=(acc_i+m_i)>>>15; end
                            1: begin b1r<=(acc_r+m_r)>>>15; b1i<=(acc_i+m_i)>>>15; end
                            2: begin b2r<=(acc_r+m_r)>>>15; b2i<=(acc_i+m_i)>>>15; end
                            3: begin b3r<=(acc_r+m_r)>>>15; b3i<=(acc_i+m_i)>>>15; end
                            4: begin b4r<=(acc_r+m_r)>>>15; b4i<=(acc_i+m_i)>>>15; end
                            5: begin b5r<=(acc_r+m_r)>>>15; b5i<=(acc_i+m_i)>>>15; end
                            6: begin b6r<=(acc_r+m_r)>>>15; b6i<=(acc_i+m_i)>>>15; end
                            7: begin b7r<=(acc_r+m_r)>>>15; b7i<=(acc_i+m_i)>>>15; end
                        endcase
                        acc_r <= 0; acc_i <= 0;  // reset for next k_idx
                        n_idx<=0;
                        if (k_idx==7)begin state<=0;done_q<=1'b1;end
                        else k_idx<=k_idx+1;
                    end else n_idx<=n_idx+1;
                end
            endcase
        end
    end
endmodule
