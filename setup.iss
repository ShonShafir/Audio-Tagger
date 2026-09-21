[Setup]
AppName=Audio Tagger
AppVersion=1.0
DefaultDirName={pf}\AudioTagger
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=AudioTagger_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=app_icon.ico

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\AudioTagger\AudioTagger.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\AudioTagger\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Audio Tagger"; Filename: "{app}\AudioTagger.exe"
Name: "{autodesktop}\Audio Tagger"; Filename: "{app}\AudioTagger.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AudioTagger.exe"; Description: "{cm:LaunchProgram,Audio Tagger}"; Flags: nowait postinstall skipifsilent
