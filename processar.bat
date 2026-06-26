@echo off
REM processar.bat - envia os PDFs de study-inbox/ para processamento na nuvem.
cd /d "%~dp0"
git add study-inbox
git commit -m "chore: novos PDFs para estudo"
git pull --rebase origin main
git push origin main
echo.
echo Enviado. O GitHub Actions vai processar e o resultado aparece na aba Estudo.
pause
