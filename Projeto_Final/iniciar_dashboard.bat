@echo off
chcp 65001 >nul
title Dashboard Taxa Selic (SGS 4390 - BCB) - Projeto CDIA

REM Muda para a pasta onde o arquivo .bat esta salvo
cd /d "%~dp0"

echo ============================================================================
echo   INICIADOR AUTOMATICO - DASHBOARD TAXA SELIC (SGS 4390 - BCB)
echo ============================================================================
echo.

set "PYTHON_CMD="

REM 1. Testa o lancador oficial do Windows (py)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto :encontrado
)

REM 2. Testa o comando python padrao (verificando se nao e o atalho falso da Microsoft Store)
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :encontrado
)

REM 3. Procura nas pastas padrao de instalacao do Python no Windows (AppData e Program Files)
for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set "PYTHON_CMD="%%D\python.exe""
        goto :encontrado
    )
)

for /d %%D in ("C:\Python3*" "%ProgramFiles%\Python3*") do (
    if exist "%%D\python.exe" (
        set "PYTHON_CMD="%%D\python.exe""
        goto :encontrado
    )
)

REM 4. Procura no Anaconda / Miniconda caso o usuario utilize Conda
if exist "%UserProfile%\anaconda3\python.exe" (
    set "PYTHON_CMD="%UserProfile%\anaconda3\python.exe""
    goto :encontrado
)
if exist "%UserProfile%\miniconda3\python.exe" (
    set "PYTHON_CMD="%UserProfile%\miniconda3\python.exe""
    goto :encontrado
)

REM 5. Caso o Python realmente nao esteja instalado na maquina, oferece instalacao via winget
echo [AVISO] O Python nao foi encontrado nas pastas padrao do Windows.
echo Tentando instalar o Python 3.12 automaticamente via Winget...
echo.
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD="%LocalAppData%\Programs\Python\Python312\python.exe""
    goto :encontrado
)

echo.
echo [ERRO] Nao foi possivel localizar o Python automaticamente.
echo Baixe e instale em https://www.python.org/downloads/ marcando a opcao "Add Python to PATH".
pause
exit /b 1

:encontrado
echo [OK] Python localizado com sucesso: %PYTHON_CMD%
echo.

echo [1/3] Verificando e instalando as bibliotecas necessarias (pandas, numpy, plotly, streamlit)...
%PYTHON_CMD% -m pip install --upgrade pip --quiet
if exist "requirements.txt" (
    %PYTHON_CMD% -m pip install -r requirements.txt
) else (
    %PYTHON_CMD% -m pip install pandas numpy plotly streamlit
)

echo.
echo [2/3] Executando validacao rapida do sistema e gerando base CSV caso necessario...
%PYTHON_CMD% app.py --test

echo.
echo [3/3] Abrindo o Dashboard Interativo no navegador...
echo (Para encerrar o servidor depois da apresentacao, basta fechar esta janela)
echo.
%PYTHON_CMD% -m streamlit run app.py

pause
