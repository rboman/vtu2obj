#define MyAppName "fossils-vtu2obj"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "fossils-vtu2obj contributors"
#define MyAppURL "https://github.com/rboman/vtu2obj"
#define MyAppExeName "fossils-vtu2obj-gui.exe"
#define MyCliExeName "fossils-vtu2obj.exe"

[Setup]
AppId={{2D13DAB9-2A31-4D8E-93D9-318F0E4F5166}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=
OutputDir=dist\installer
OutputBaseFilename=fossils-vtu2obj-setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "addtopath"; Description: "Add installation folder to system PATH"; GroupDescription: "Command-line integration:"; Flags: unchecked

[Files]
Source: "dist\fossils_vtu2obj\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "examples\*.vtu"; DestDir: "{app}\examples"; Flags: ignoreversion
Source: "examples\README.md"; DestDir: "{app}\examples"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
const
  EnvironmentKey = 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment';

function AddDirToPath(DirName: string): Boolean;
var
  OldPath: string;
begin
  Result := False;
  if not RegQueryStringValue(HKLM, EnvironmentKey, 'Path', OldPath) then
    OldPath := '';

  if Pos(';' + Uppercase(DirName) + ';', ';' + Uppercase(OldPath) + ';') > 0 then
  begin
    Result := True;
    exit;
  end;

  if (OldPath <> '') and (OldPath[Length(OldPath)] <> ';') then
    OldPath := OldPath + ';';

  Result := RegWriteStringValue(HKLM, EnvironmentKey, 'Path', OldPath + DirName);
end;

function RemoveDirFromPath(DirName: string): Boolean;
var
  OldPath: string;
  Search: string;
  StartPos: Integer;
begin
  Result := False;
  if not RegQueryStringValue(HKLM, EnvironmentKey, 'Path', OldPath) then
  begin
    Result := True;
    exit;
  end;

  Search := ';' + Uppercase(DirName) + ';';
  OldPath := ';' + OldPath + ';';
  StartPos := Pos(Search, Uppercase(OldPath));

  while StartPos > 0 do
  begin
    Delete(OldPath, StartPos, Length(Search) - 1);
    StartPos := Pos(Search, Uppercase(OldPath));
  end;

  if (Length(OldPath) > 0) and (OldPath[1] = ';') then
    Delete(OldPath, 1, 1);
  if (Length(OldPath) > 0) and (OldPath[Length(OldPath)] = ';') then
    Delete(OldPath, Length(OldPath), 1);

  Result := RegWriteStringValue(HKLM, EnvironmentKey, 'Path', OldPath);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('addtopath') then
  begin
    if AddDirToPath(ExpandConstant('{app}')) then
      Log('Added install directory to PATH: ' + ExpandConstant('{app}'));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    if RemoveDirFromPath(ExpandConstant('{app}')) then
      Log('Removed install directory from PATH: ' + ExpandConstant('{app}'));
  end;
end;
