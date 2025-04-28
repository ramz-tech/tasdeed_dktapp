; -- Inno Setup Script for tasdeed_dktapp --

[Setup]
AppName=ORION Data Extractor
AppVersion=1.0
DefaultDirName={pf}\ORION Data Extractor
DefaultGroupName=ORION Data Extractor
OutputDir=Output
OutputBaseFilename=ORION_Data_Extractor_Installer
Compression=lzma
SolidCompression=yes

[Files]
; Add the main executable file (compiled from main.py using PyInstaller)
Source: "dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion

; Include additional Python files or assets if needed
; Example: Source: "path\to\your\python_files\*"; DestDir: "{app}\python_files"; Flags: ignoreversion recursesubdirs createallsubdirs

; Include any icons or resources
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Shortcut to launch the application
Name: "{group}\ORION Data Extractor"; Filename: "{app}\main.exe"

; Shortcut to uninstall the application
Name: "{group}\Uninstall ORION Data Extractor"; Filename: "{uninstallexe}"

[Run]
; Run the application after installation
Filename: "{app}\main.exe"; Description: "Launch ORION Data Extractor"; Flags: nowait postinstall skipifsilent
