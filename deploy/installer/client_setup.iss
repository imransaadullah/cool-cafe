; CyberCafe Client Installer Script
; Using Inno Setup

#define MyAppName "CyberCafe Client"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CyberCafe"
#define MyAppURL "https://cybercafe.com"
#define MyAppExeName "CyberCafe Client.exe"

[Setup]
AppId={{B2C3D4E5-F6A7-8901-BCDE-F12345678901}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\CyberCafe Client
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=cybercafe_client_setup
SetupIconFile=resources\client_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "installservice"; Description: "Install Watchdog Service"; GroupDescription: "Service:"; Flags: checkedonce
Name: "autostart"; Description: "Start with Windows"; GroupDescription: "Startup:"; Flags: checkedonce

[Files]
Source: "dist\CyberCafe Client\CyberCafe Client.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\CyberCafe Client\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "config.example.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; Auto-start on boot
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CyberCafeClient"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

; Disable Task Manager (optional security)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Policies\System"; ValueType: dword; ValueName: "DisableTaskMgr"; ValueData: "0"; Flags: uninsdeletevalue

[Code]
// Check if server is reachable
function IsServerReachable: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd', '/c ping -n 1 localhost', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function InitializeSetup: Boolean;
var
  ConfigFile: string;
  ServerURL: string;
begin
  Result := True;
  
  ConfigFile := ExpandConstant('{app}\config.json');
  
  // Check if config exists
  if not FileExists(ConfigFile) then
  begin
    ServerURL := InputBox('Server Configuration', 'Enter the cafe server IP (e.g. http://192.168.1.100:8000):', '');
    if ServerURL = '' then
      ServerURL := 'http://192.168.1.100:8000';
    
    // Create config file (setup wizard runs on first launch)
    SaveStringToFile(ConfigFile, 
      '{' + #13#10 +
      '  "configured": false,' + #13#10 +
      '  "server_url": "' + ServerURL + '",' + #13#10 +
      '  "pc_id": 1,' + #13#10 +
      '  "pc_number": 1,' + #13#10 +
      '  "branch_id": 1,' + #13#10 +
      '  "heartbeat_interval": 5,' + #13#10 +
      '  "offline_mode": false' + #13#10 +
      '}', False);
  end;
end;
