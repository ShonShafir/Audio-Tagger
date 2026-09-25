# Auto-build script for Portable Audio Tagger
# This creates a standalone Windows environment bypassing PyInstaller/Windows Defender issues.

Write-Host "Cleaning old builds..."
Remove-Item -Recurse -Force PortableAudioTagger -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force Output -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
Remove-Item AudioTagger.spec -ErrorAction SilentlyContinue

Write-Host "Creating Portable Python Environment..."
mkdir PortableAudioTagger | Out-Null
cd PortableAudioTagger

Write-Host "Downloading Python 3.11 Embeddable..."
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -OutFile "python-embed.zip"
Expand-Archive -Path "python-embed.zip" -DestinationPath "."
rm "python-embed.zip"

Write-Host "Enabling pip and installing dependencies..."
(Get-Content "python311._pth") -replace "#import site", "import site" | Set-Content "python311._pth"
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "get-pip.py"
.\python.exe get-pip.py
.\python.exe -m pip install PyQt6 mutagen requests ytmusicapi

Write-Host "Copying Audio Tagger application files..."
Copy-Item "..\app.py" -Destination "."
Copy-Item "..\app_icon.ico" -Destination "."
Copy-Item -Path "..\core" -Destination "core" -Recurse
cd ..

Write-Host "Compiling Inno Setup Installer..."
& "C:\Users\User\AppData\Local\Programs\Inno Setup 6\ISCC.exe" setup.iss

Write-Host "Done! Installer is located in Output/AudioTagger_Setup.exe"
