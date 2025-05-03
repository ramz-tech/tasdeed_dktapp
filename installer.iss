; Inno Setup Script for ORION Application

[Setup]
AppName=ORION
AppVersion=1.0
AppPublisher=ORION
AppPublisherURL=http://www.ORION.com
AppSupportURL=http://www.ORION.com/support
AppUpdatesURL=http://www.ORION.com/updates
DefaultDirName={pf}\ORION
DefaultGroupName=ORION
OutputBaseFilename=ORION_Setup
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Replace the Source path to the location of your ORION.exe file after building the project.
Source: "dist\ORION.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ORION"; Filename: "{app}\ORION.exe"

[Run]
Filename: "{app}\ORION.exe"; Description: "Launch ORION"; Flags: nowait postinstall skipifsilent
