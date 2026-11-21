@echo off
echo Timing the first 96 demo frames in both Tandy modes...
DOOM -tandy -timedemo demo3 -quick > FAST.LOG
if errorlevel 1 goto failed
DOOM -tandyhi -timedemo demo3 -quick > FULL.LOG
if errorlevel 1 goto failed
echo Fast:
find "Timed " FAST.LOG
echo Full detail:
find "Timed " FULL.LOG
goto end
:failed
echo Benchmark stopped. See FAST.LOG and FULL.LOG.
:end
