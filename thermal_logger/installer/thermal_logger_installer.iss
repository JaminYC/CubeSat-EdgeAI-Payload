#define MyAppName "Thermal Logger"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Thermal Logger Team"
#define MyAppURL "https://example.local/thermal-logger"
#define MyAppExeName "thermal_logger_gui.exe"

[Setup]
AppId={{7B664901-18F4-4B48-B583-CB7D0511A875}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Thermal Logger
DefaultGroupName=Thermal Logger
AllowNoIcons=yes
LicenseFile=
OutputDir=..\dist
OutputBaseFilename=thermal_logger_setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\dist\thermal_logger_gui.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\DRIVERS.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Thermal Logger"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Guia de drivers"; Filename: "{app}\DRIVERS.md"
Name: "{group}\Desinstalar Thermal Logger"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Thermal Logger"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar Thermal Logger"; Flags: nowait postinstall skipifsilent
