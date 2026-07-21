# Auto-generated Vivado synthesis script
# Project: bram_acc  |  Part: xc7a200t-fbg484-2L

set output_dir {C:\Users\12430\Desktop\ai_verilog_auto_tools\outputs\bram_acc\vivado_synth\vivado_out}
file mkdir $output_dir

create_project -force bram_acc _bram_acc -part xc7a200t-fbg484-2L

# Add source files
add_files -norecurse {C:/Users/12430/Desktop/ai_verilog_auto_tools/outputs/bram_acc/src/bram_acc.sv}
add_files -norecurse {C:/Users/12430/Desktop/ai_verilog_auto_tools/ip_models/bram/ip_bram.sv}
set_property top bram_acc [current_fileset]
update_compile_order -fileset sources_1

# Add constraint files
add_files -fileset constrs_1 -norecurse {C:/Users/12430/Desktop/ai_verilog_auto_tools/outputs/bram_acc/constraints.xdc}

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
    file copy -force $bit_file $output_dir/bram_acc.bit
    puts "BITSTREAM: $output_dir/bram_acc.bit"
}

puts "=== DONE ==="
exit
