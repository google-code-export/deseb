@echo off
for /D %%a in (case* issue*) do cd %%a\ && del models.py 1>nul 2>nul && copy models.py.pre models.py > nul && cd ..
