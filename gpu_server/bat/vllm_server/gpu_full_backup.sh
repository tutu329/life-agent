sudo nvidia-smi -pm 1 # Set persistence mode: 0/DISABLED, 1/ENABLED
sudo nvidia-smi -lgc 1400 # Specifies <minGpuClock,maxGpuClock> clocks as a
#                                    pair (e.g. 1500,1500) that defines the range
#                                    of desired locked GPU clock speed in MHz.
#                                    Setting this will supercede application clocks
#                                    and take effect regardless if an app is running.
#                                    Input can also be a singular desired clock value
#                                    (e.g. <GpuClockValue>). Optionally, --mode can be
#                                    specified to indicate a special mode.
sudo nvidia-smi -lmc 6500 # Specifies <minMemClock,maxMemClock> clocks as a
#                                    pair (e.g. 5100,5100) that defines the range
#                                    of desired locked Memory clock speed in MHz.
#                                    Input can also be a singular desired clock value
#                                    (e.g. <MemClockValue>).
sudo nvidia-smi -gtt 65 #  Set GPU Target Temperature for a GPU in degree celsius.
#                                Requires administrator privileges
sudo nvidia-smi -cc 1 # Overrides or restores default CUDA clocks.
#                                In override mode, GPU clocks higher frequencies when running CUDA applications.
#                                Only on supported devices starting from the Volta series.
#                                Requires administrator privileges.
#                                0/RESTORE_DEFAULT, 1/OVERRIDE
sudo nvidia-smi -pl 200 # Specifies maximum power management limit in watts.
#                                Takes an optional argument --scope.
