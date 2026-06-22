; CyberCafe Unified Installer
; One installer — user picks Local Server, Global Server, or Client PC

#define MyAppPublisher "CyberCafe"
#define MyAppVersion "1.0.0"
#define MyAppURL "https://cybercafe.com"

[Setup]
AppId={{C4F8E2A1-9B3D-4E7F-A1C2-5D6E8F0A2B4C}
AppName=CyberCafe
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={code:GetInstallDir}
DefaultGroupName=CyberCafe
OutputDir=installer_output
OutputBaseFilename=cybercafe_setup
SetupIconFile=resources\server_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "local"; Description: "Local Server — single café (API + dashboard + setup wizard)"
Name: "global"; Description: "Global Server — multi-site owner / sync hub"
Name: "client"; Description: "Client — install on customer / gaming PCs"
Name: "custom"; Description: "Custom"; Flags: iscustom

[Components]
Name: "localapp"; Description: "Local Server application"; Types: local
Name: "globalapp"; Description: "Global Server application"; Types: global
Name: "clientapp"; Description: "Client application"; Types: client

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "localautostart"; Description: "Start Local Server when Windows starts"; GroupDescription: "Local Server:"; Components: localapp; Flags: checkedonce
Name: "clientwatchdog"; Description: "Install client watchdog service"; GroupDescription: "Client:"; Components: clientapp; Flags: checkedonce
Name: "clientautostart"; Description: "Start client when Windows starts"; GroupDescription: "Client:"; Components: clientapp; Flags: checkedonce

[Files]
; --- Local Server ---
Source: "payload\local_server\*"; DestDir: "{app}"; Components: localapp; Flags: ignoreversion recursesubdirs createallsubdirs
; --- Global Server ---
Source: "payload\global_server\*"; DestDir: "{app}"; Components: globalapp; Flags: ignoreversion recursesubdirs createallsubdirs
; --- Client ---
Source: "payload\client\*"; DestDir: "{app}"; Components: clientapp; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CyberCafe Local Server"; Filename: "{app}\CyberCafe Server.exe"; Components: localapp
Name: "{group}\CyberCafe Global Server"; Filename: "{app}\CyberCafe Global Server.exe"; Components: globalapp
Name: "{group}\CyberCafe Client"; Filename: "{app}\CyberCafe Client.exe"; Components: clientapp
Name: "{group}\Uninstall CyberCafe"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CyberCafe Local Server"; Filename: "{app}\CyberCafe Server.exe"; Tasks: desktopicon; Components: localapp
Name: "{autodesktop}\CyberCafe Global Server"; Filename: "{app}\CyberCafe Global Server.exe"; Tasks: desktopicon; Components: globalapp
Name: "{autodesktop}\CyberCafe Client"; Filename: "{app}\CyberCafe Client.exe"; Tasks: desktopicon; Components: clientapp

[Run]
Filename: "{app}\CyberCafe Server.exe"; Description: "Launch Local Server setup"; Components: localapp; Flags: nowait postinstall skipifsilent
Filename: "{app}\CyberCafe Global Server.exe"; Description: "Launch Global Server setup"; Components: globalapp; Flags: nowait postinstall skipifsilent
Filename: "{app}\CyberCafeWatchdog.exe"; Parameters: "install"; Components: clientapp; Tasks: clientwatchdog; Flags: runhidden waituntilterminated
Filename: "{app}\CyberCafeWatchdog.exe"; Parameters: "start"; Components: clientapp; Tasks: clientwatchdog; Flags: runhidden waituntilterminated
Filename: "{app}\CyberCafe Client.exe"; Parameters: "--install-autostart"; Components: clientapp; Tasks: clientautostart; Flags: runhidden waituntilterminated
Filename: "{app}\CyberCafe Client.exe"; Description: "Launch client setup"; Components: clientapp; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\CyberCafeWatchdog.exe"; Parameters: "stop"; Components: clientapp; Flags: runhidden waituntilterminated
Filename: "{app}\CyberCafeWatchdog.exe"; Parameters: "remove"; Components: clientapp; Flags: runhidden waituntilterminated
Filename: "{app}\CyberCafeCleanup.exe"; Parameters: """{app}"""; Components: clientapp; Flags: runhidden waituntilterminated

[Registry]
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CyberCafeLocalServer"; ValueData: """{app}\CyberCafe Server.exe"""; Flags: uninsdeletevalue; Components: localapp; Tasks: localautostart
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CyberCafeClient"; ValueData: """{app}\CyberCafe Client.exe"""; Flags: uninsdeletevalue; Components: clientapp; Tasks: clientautostart

[Code]
function IsLocal: Boolean;
begin
  Result := IsComponentSelected('localapp');
end;

function IsGlobal: Boolean;
begin
  Result := IsComponentSelected('globalapp');
end;

function IsClient: Boolean;
begin
  Result := IsComponentSelected('clientapp');
end;

function GetInstallDir(Param: String): String;
begin
  if IsLocal then
    Result := ExpandConstant('{autopf}\CyberCafe Local Server')
  else if IsGlobal then
    Result := ExpandConstant('{autopf}\CyberCafe Global Server')
  else if IsClient then
    Result := ExpandConstant('{autopf}\CyberCafe Client')
  else
    Result := ExpandConstant('{autopf}\CyberCafe');
end;

function GetAppTitle(Param: String): String;
begin
  if IsLocal then
    Result := 'CyberCafe Local Server'
  else if IsGlobal then
    Result := 'CyberCafe Global Server'
  else if IsClient then
    Result := 'CyberCafe Client'
  else
    Result := 'CyberCafe';
end;

function GetMainExe(Param: String): String;
begin
  if IsLocal then
    Result := ExpandConstant('{app}\CyberCafe Server.exe')
  else if IsGlobal then
    Result := ExpandConstant('{app}\CyberCafe Global Server.exe')
  else if IsClient then
    Result := ExpandConstant('{app}\CyberCafe Client.exe')
  else
    Result := '';
end;

function InitializeSetup: Boolean;
begin
  Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpSelectComponents then
  begin
    if not IsComponentSelected('localapp') and not IsComponentSelected('globalapp') and not IsComponentSelected('clientapp') then
    begin
      MsgBox('Please select an installation type (Local Server, Global Server, or Client).', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    if (Ord(IsComponentSelected('localapp')) + Ord(IsComponentSelected('globalapp')) + Ord(IsComponentSelected('clientapp'))) > 1 then
    begin
      MsgBox('Please install only one type per machine (Local, Global, or Client).', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpSelectDir) or (CurPageID = wpSelectComponents) then
    WizardForm.DirEdit.Text := GetInstallDir('');
end;
