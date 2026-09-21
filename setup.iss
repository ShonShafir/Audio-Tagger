[Setup]
AppName=Audio Tagger
AppVersion=1.0.0
DefaultDirName={autopf}\AudioTagger
DefaultGroupName=Audio Tagger
UninstallDisplayIcon={app}\app_icon.ico
Compression=lzma2
SolidCompression=yes
OutputDir=Output
OutputBaseFilename=AudioTagger_Setup
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "PortableAudioTagger\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Audio Tagger"; Filename: "{app}\pythonw.exe"; Parameters: "app.py"; WorkingDir: "{app}"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\Audio Tagger"; Filename: "{app}\pythonw.exe"; Parameters: "app.py"; WorkingDir: "{app}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Run]
Filename: "{app}\pythonw.exe"; Parameters: "app.py"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,Audio Tagger}"; Flags: nowait postinstall skipifsilent
