function Invoke-ISE {
    param([string]$Command)
    $batContent = @"
@echo off
set XILINX=C:\Xilinx\14.7\ISE_DS\ISE
set PATH=C:\Xilinx\14.7\ISE_DS\ISE\bin\nt64;C:\Xilinx\14.7\ISE_DS\ISE\lib\nt64;C:\Xilinx\14.7\ISE_DS\common\bin\nt64;C:\Xilinx\14.7\ISE_DS\common\lib\nt64;%PATH%
cd /d Z:\
$Command
"@
    $batContent | Set-Content "C:\FPGA_Projects\_ise_cmd.bat" -Encoding ASCII
    & 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' guestcontrol Win7-ISE run --username 'Daiguanzi' --password '1234' --wait-stdout --exe 'C:\Windows\System32\cmd.exe' -- cmd /c 'Z:\_ise_cmd.bat'
}
Write-Host "ISE wrapper loaded. Usage: Invoke-ISE 'xst -ifn design.xst -ofn design.ngc'"