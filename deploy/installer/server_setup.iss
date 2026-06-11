; CyberCafe Server Installer Script
; Using Inno Setup

#define MyAppName "CyberCafe Server"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CyberCafe"
#define MyAppURL "https://cybercafe.com"
#define MyAppExeName "CyberCafe Server.exe"

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
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "installservice"; Description: "Install as Windows Service"; GroupDescription: "Service:"; Flags: checkedonce

[Files]
Source: "dist\CyberCafe Server\CyberCafe Server.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\CyberCafe Server\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; Auto-start on boot
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CyberCafeServer"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue

[Code]
// Check if PostgreSQL is installed
function IsPostgreSQLInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd', '/c pg_isready', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// Check if port is available
function IsPortAvailable(Port: Integer): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd', '/c netstat -an | findstr ' + IntToStr(Port), '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode <> 0);
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  
  if not IsPostgreSQLInstalled then
  begin
    if MsgBox('PostgreSQL is not installed. Would you like to download it?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec('cmd', '/c start https://www.postgresql.org/download/windows/', '', SW_SHOW, ewNoWait);
    end;
  end;
end;
