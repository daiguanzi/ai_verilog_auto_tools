# Auto-generated Vivado synthesis script
# Project: dft8_axi_top  |  Part: xc7a200t-fbg484-2L

set output_dir {C:\Users\12430\Desktop\ai_verilog_auto_tools\outputs\dft8_axi\vivado_synth\vivado_out}
file mkdir $output_dir

create_project -force dft8_axi_top _dft8_axi_top -part xc7a200t-fbg484-2L

# Add source files
add_files -norecurse {C:/Users/12430/Desktop/ai_verilog_auto_tools/outputs/dft8_axi/src/dft8_axi_top.sv}
set_property top dft8_axi_top [current_fileset]
update_compile_order -fileset sources_1

# Add constraint files
add_files -fileset constrs_1 -norecurse {C:/Users/12430/Desktop/ai_verilog_auto_tools/outputs/dft8_axi/constraints.xdc}

# Run synthesis
puts "=== SYNTHESIS ==="
launch_runs synth_1
wait_on_run synth_1

# Write utilisation report
open_run synth_1
report_utilization -file $output_dir/utilization.rpt

# Run implementation
puts "=== IMPLEMENTATION ==="
launch_runs impl_1 -to_step write_bitstream
wait_on_run impl_1

# Timing report
open_run impl_1
report_timing_summary -file $output_dir/timing.rpt

# Export bitstream path
set bit_file [glob -nocomplain [get_property directory [current_run]]/*.bit]
if {$bit_file ne ""} {
    file copy -force $bit_file $output_dir/dft8_axi_top.bit
    puts "BITSTREAM: $output_dir/dft8_axi_top.bit"
}

puts "=== DONE ==="
exit
