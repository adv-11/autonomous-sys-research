@echo off
rem Claude Opus: independent deadline watchdog. Stops ONLY this task's session name.
set LOG=C:\Users\Advait\autonomous-sys-research\outputs\rtdetr_transfer_20261123\watchdog.log
echo %DATE% %TIME% watchdog fired for %1 >> %LOG%
C:\Users\Advait\.local\bin\colab.exe stop -s %1 >> %LOG% 2>&1
C:\Users\Advait\.local\bin\colab.exe sessions >> %LOG% 2>&1
C:\Users\Advait\.local\bin\colab.exe usage >> %LOG% 2>&1
