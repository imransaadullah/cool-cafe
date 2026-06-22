; CyberCafe Server Installer Script
; Installs server manager (API + dashboard) with optional Windows service

#define MyAppName "CyberCafe Server"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CyberCafe"
#define MyAppURL "https://cybercafe.com"
#define MyAppExeName "CyberCafe Server.exe"
#define MyServiceExeName "CyberCafeServerService.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\CyberCafe Server
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=cybercafe_server_setup
SetupIconFile=resources\server_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "installservice"; Description: "Install as Windows Service (auto-restart)"; GroupDescription: "Service:"; Flags: unchecked
Name: "autostart"; Description: "Start server manager when Windows starts"; GroupDescription: "Startup:"; Flags: checkedonce

[Files]
Source: "..\..\local_server\dist\CyberCafe Server\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\local_server\dist\CyberCafe Server\{#MyServiceExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\local_server\dist\CyberCafe Server\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\.env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyServiceExeName}"; Parameters: "install"; StatusMsg: "Installing server service..."; Tasks: installservice; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyServiceExeName}"; Parameters: "start"; StatusMsg: "Starting server service..."; Tasks: installservice; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "Launch setup wizard"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#MyServiceExeName}"; Parameters: "stop"; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyServiceExeName}"; Parameters: "remove"; Flags: runhidden waituntilterminated

[Registry]
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CyberCafeServer"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;
