; Instalador de Windows (Inno Setup), copia del de Programaciones. Lo compila la CI (compilar.yml), nunca en local.
; AppId propio y FIJO: con él, cada versión nueva sustituye a la anterior. No se cambia nunca.
#define MyAppName "PCCF"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppPublisher "Carlos Ferrero Bonet"
#define MyAppExeName "PCCF.exe"

[Setup]
AppId={{85470BD6-8808-4C8A-80ED-753B6F74C00E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\PCCF
DefaultGroupName=PCCF
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir=Output
OutputBaseFilename=PCCF-{#MyAppVersion}-Windows-Setup
ArchitecturesInstallIn64BitMode=x64compatible
; Sin exigir administrador: en el centro casi nadie lo es.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll,*.pyd
RestartApplications=no
SetupIconFile=imagenes\icono.ico

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear icono en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "dist\PCCF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PCCF"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\PCCF"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir PCCF"; Flags: nowait postinstall skipifsilent

[Code]
{ El registro vive en %APPDATA%\PCCF, fuera del programa, y desinstalar no lo toca. Los datos del PCCF están en
  la carpeta de datos que se elige en Ajustes. }

function DesinstaladorAnterior(): String;
var
  Clave: String;
  Valor: String;
begin
  Result := '';
  Clave := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
           ExpandConstant('{#SetupSetting("AppId")}') + '_is1';
  if RegQueryStringValue(HKCU, Clave, 'UninstallString', Valor) then
    Result := Valor
  else if RegQueryStringValue(HKLM, Clave, 'UninstallString', Valor) then
    Result := Valor;
  Result := RemoveQuotes(Result);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Desinstalador: String;
  Codigo: Integer;
  Espera: Integer;
begin
  Result := '';
  Desinstalador := DesinstaladorAnterior();
  if (Desinstalador = '') or (not FileExists(Desinstalador)) then
    exit;
  if not Exec(Desinstalador, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '',
              SW_HIDE, ewWaitUntilTerminated, Codigo) then
    exit;
  Espera := 0;
  while FileExists(Desinstalador) and (Espera < 60) do
  begin
    Sleep(500);
    Espera := Espera + 1;
  end;
end;
