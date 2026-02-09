REM Override POSTGRES_CONNECTION_STRING to use host.docker.internal so the container
REM can connect to PostgreSQL running on the host (127.0.0.1 inside container is the container itself)
set POSTGRES_DOCKER_STR="postgresql://postgres:Sarovar16108^!^!@host.docker.internal:5432/knowledge_base_server"


@echo off
REM Batch file to run the Docker application with all environment variables from .env
REM Make sure Docker is running and the image is built (use docker_build.ps1 or docker build)

setlocal enabledelayedexpansion

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running. Please start Docker Desktop and try again.
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo ERROR: .env file not found in the current directory.
    exit /b 1
)

REM Read PORT from .env file (default to 9999 if not found)
set PORT=9999
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if /i "%%a"=="PORT" (
        set PORT=%%b
        goto :port_found
    )
)
:port_found

REM Remove any spaces from PORT
set PORT=!PORT: =!

REM Set image name (should match the one built with docker_build.ps1)
set IMAGE_NAME=graphrag_kb_server

REM Check if image exists
docker images %IMAGE_NAME% --format "{{.Repository}}" | findstr /C:"%IMAGE_NAME%" >nul
if errorlevel 1 (
    echo WARNING: Docker image '%IMAGE_NAME%' not found.
    echo Please build the image first using: docker build -t %IMAGE_NAME% .
    echo Or run: docker_build.ps1
    echo.
    set /p BUILD_NOW="Do you want to build it now? (Y/N): "
    if /i "!BUILD_NOW!"=="Y" (
        docker build -t %IMAGE_NAME% .
        if errorlevel 1 (
            echo ERROR: Failed to build Docker image.
            exit /b 1
        )
    ) else (
        exit /b 1
    )
)

REM Set local directory for data (change this to your desired path)
set LOCAL_DATA_DIR=C:\var\graphrag

REM Create local directory if it doesn't exist
if not exist "%LOCAL_DATA_DIR%" (
    echo Creating local directory '%LOCAL_DATA_DIR%'...
    mkdir "%LOCAL_DATA_DIR%"
)

echo.
echo Starting Docker container...
echo Image: %IMAGE_NAME%
echo Port: %PORT%
echo Environment: .env file
if defined POSTGRES_DOCKER_STR echo Database: host.docker.internal (override for local PostgreSQL on host)
echo Volume: %LOCAL_DATA_DIR%:/var/graphrag
echo.



REM Run the Docker container with all environment variables from .env.
REM If POSTGRES_CONNECTION_STRING was found, override it to use host.docker.internal.
if defined POSTGRES_DOCKER_STR (
    docker run --rm -it ^
        --name graphrag_kb_server ^
        -p %PORT%:%PORT% ^
        --env-file .env ^
        -e "POSTGRES_CONNECTION_STRING=!POSTGRES_DOCKER_STR!" ^
        -e "SERVER=0.0.0.0" ^
        -v "%LOCAL_DATA_DIR%:/var/graphrag" ^
        %IMAGE_NAME%
) else (
    docker run --rm -it ^
        --name graphrag_kb_server ^
        -p %PORT%:%PORT% ^
        --env-file .env ^
        -e "SERVER=0.0.0.0" ^
        -v "%LOCAL_DATA_DIR%:/var/graphrag" ^
        %IMAGE_NAME%
)

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start Docker container.
    exit /b 1
)

endlocal
