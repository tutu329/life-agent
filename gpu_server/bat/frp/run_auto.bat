@echo off
echo 当前目录：%~dp0 >>log.txt
if not exist %~dp0frpc.exe (
	echo %~dp0frpc.exe 文件不存在 >>log.txt
	exit
)
echo %date% %time% 正终止其它的FRPC进程 >>log.txt
taskkill /f /im frpc.exe
echo %date% %time% 已经终止全部的FRPC进程 >>log.txt
echo %date% %time% 正在启动FRPC >>log.txt
start /wait frpc.exe -c frpc.ini
echo %date% %time% FRPC发生中断 >>log.txt
run_auto.bat