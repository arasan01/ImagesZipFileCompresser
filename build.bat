@echo off
cd /d %~dp0

SET TARGET=compresser

python -OO -m PyInstaller %TARGET%.py --clean
copy 7z.dll .\\dist\\%TARGET%\\
copy 7z.exe .\\dist\\%TARGET%\\
copy convert.exe .\\dist\\%TARGET%\\
mkdir .\\dist\\%TARGET%\\config
copy config\\config.json .\\dist\\%TARGET%\\config
