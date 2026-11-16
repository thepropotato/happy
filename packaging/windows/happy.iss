; Builds dist\Happy-Setup.exe: installs Happy's code for this user only and adds a Start menu shortcut that sets it up on first open.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6C1F3A52-8E0B-4C7A-9D2E-5B7A1C4F8E31}
AppName=Happy
AppVersion={#AppVersion}
AppPublisher=thepropotato
AppPublisherURL=https://github.com/thepropotato/happy
DefaultDirName={localappdata}\Programs\Happy
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=Happy-Setup
SetupIconFile=happy.ico
UninstallDisplayIcon={app}\happy.ico
UninstallDisplayName=Happy
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Put Happy on the desktop"; Flags: unchecked

[Files]
Source: "..\..\dist\windows\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "launch.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "happy.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\Happy"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\launch.ps1"""; IconFilename: "{app}\happy.ico"
Name: "{userdesktop}\Happy"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\launch.ps1"""; IconFilename: "{app}\happy.ico"; Tasks: desktopicon

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\launch.ps1"""; Description: "Open Happy"; Flags: postinstall nowait skipifsilent runhidden
