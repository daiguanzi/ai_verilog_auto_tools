create_clock -period 10.000 -name wclk [get_ports wclk]
create_clock -period 12.000 -name rclk [get_ports rclk]
set_clock_groups -asynchronous -group [get_clocks wclk] -group [get_clocks rclk]
