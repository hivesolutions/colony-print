; Inno Setup (https://jrsoftware.org/isinfo.php) script of the Colony Print node
; installer for Windows, that installs an embedded Python with the node packages
; (colony-print, npcolony and their dependencies) and registers the node as a
; Windows service, built by the windows\build.ps1 script.
;
; Besides the wizard, the installer may be run silently with the configuration
; of the node provided as parameters, for example:
;
;   colony-print-node-setup.exe /VERYSILENT /URL=https://print.example.com/
;     /KEY=secret /NAME="Shop 1" /LOCATION=Porto /PRINTER="EPSON TM-T20II"
;
; Other parameters are /ID, /MODE (normal or email), /EMAILS, /MAILMEKEY,
; /MAILMEURL and /CONFIG (path to a config.env file with the values to use).
;
; The installer of the Windows XP nodes (32 bit) is the one compiled with the
; XP definition and with Inno Setup 5 (the last one that supports Windows XP),
; that installs a Python extracted from its installer, with NSSM as the service
; wrapper, as WinSW requires a .NET Framework that Windows XP lacks.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef BuildDir
  #define BuildDir "..\build\windows"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif

#define AppName "Colony Print Node"
#define ServiceName "colony-print-node"

; the name of the installer and the constant of the program files directory,
; as Inno Setup 5 has no constant for the one common to every user
#ifdef XP
  #define SetupName "colony-print-node-setup-xp"
  #define ProgramFiles "{pf}"
#else
  #define SetupName "colony-print-node-setup"
  #define ProgramFiles "{commonpf}"
#endif

[Setup]
AppId={{08AC6285-8BAA-453D-8EF4-72F19B392ED3}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Hive Solutions Lda.
AppPublisherURL=https://github.com/hivesolutions/colony-print
AppSupportURL=https://github.com/hivesolutions/colony-print/issues
DisableDirPage=yes
DisableProgramGroupPage=yes
#ifdef XP
DefaultDirName={pf}\{#AppName}
MinVersion=5.1sp3
#else
DefaultDirName={autopf}\{#AppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
#endif
PrivilegesRequired=admin
CloseApplications=no
OutputDir={#OutputDir}
OutputBaseFilename={#SetupName}-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\python\python.exe
VersionInfoVersion={#AppVersion}

[InstallDelete]
; removes the previous Python installation (including the packages installed
; by the self-update) so that no stale package is left behind
Type: filesandordirs; Name: "{app}\python"

[Files]
Source: "{#BuildDir}\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs
; the service wrapper of the Windows XP nodes (NSSM) has no configuration
; file, as the service is configured by the installer, that also runs the
; redistributable of the Visual C++ 2008 runtime required by their Python
#ifdef XP
Source: "{#BuildDir}\nssm.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#BuildDir}\vcredist_x86.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
#else
Source: "{#BuildDir}\{#ServiceName}.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "service.xml"; DestDir: "{app}"; DestName: "{#ServiceName}.xml"; Flags: ignoreversion
#endif
; the boot script is run from a copy outside of the packages updated by it,
; so that an interrupted (or broken) update never prevents the service from
; starting and updating the packages once more
Source: "{#BuildDir}\boot.py"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\{#AppName}"
Name: "{commonappdata}\{#AppName}\logs"

[UninstallRun]
Filename: "{sys}\net.exe"; Parameters: "stop {#ServiceName}"; Flags: runhidden waituntilterminated; RunOnceId: "StopService"
#ifdef XP
Filename: "{app}\nssm.exe"; Parameters: "remove {#ServiceName} confirm"; Flags: runhidden waituntilterminated; RunOnceId: "DeleteService"
#else
Filename: "{app}\{#ServiceName}.exe"; Parameters: "uninstall"; Flags: runhidden waituntilterminated; RunOnceId: "DeleteService"
#endif

[UninstallDelete]
; the configuration and the logs of the node are kept, so that they're
; reused in case the node is installed again
Type: filesandordirs; Name: "{app}\python"

[Code]
const
  ServiceName = '{#ServiceName}';
  DefaultUrl = 'https://print.bemisc.com/';
  PdfPrinter = 'Microsoft Print to PDF';

var
  ServerPage: TInputQueryWizardPage;
  ModePage: TInputOptionWizardPage;
  NodePage: TInputQueryWizardPage;
  EmailPage: TInputQueryWizardPage;
  Config: TArrayOfString;
  ParamConfig: TArrayOfString;
  DetectedPrinter: String;
  ServiceError: Boolean;

function DataDir: String;
begin
  Result := ExpandConstant('{commonappdata}\{#AppName}');
end;

function ConfigPath: String;
begin
  Result := DataDir + '\config.env';
end;

{ Parses a (.env like) configuration line into its key and value,
  using the same rules as the boot script of the node (and appier) }
function ParseLine(Line: String; var Key, Value: String): Boolean;
var
  Index: Integer;
begin
  Result := False;
  Line := Trim(Line);
  if (Line = '') or (Line[1] = '#') then
    Exit;
  Index := Pos('=', Line);
  if Index = 0 then
    Exit;
  Key := Trim(Copy(Line, 1, Index - 1));
  Value := Trim(Copy(Line, Index + 1, Length(Line)));
  if (Length(Value) > 1) and (Value[1] = Value[Length(Value)]) and
    ((Value[1] = '"') or (Value[1] = '''')) then
  begin
    Value := Copy(Value, 2, Length(Value) - 2);
    StringChangeEx(Value, '\"', '"', True);
  end;
  Result := True;
end;

{ Builds the configuration line of the provided value, quoting (and escaping)
  the value when it starts and ends with a quote, so that it's parsed back
  (by the boot script of the node) with the same value }
function ConfigLine(const Name, Value: String): String;
var
  Quoted: String;
begin
  Result := Name + '=' + Value;
  if (Length(Value) > 1) and (Value[1] = Value[Length(Value)]) and
    ((Value[1] = '"') or (Value[1] = '''')) then
  begin
    Quoted := Value;
    StringChangeEx(Quoted, '"', '\"', True);
    Result := Name + '="' + Quoted + '"';
  end;
end;

function FindConfig(const Lines: TArrayOfString; const Name: String): Integer;
var
  I: Integer;
  Key, Value: String;
begin
  Result := -1;
  for I := 0 to GetArrayLength(Lines) - 1 do
    if ParseLine(Lines[I], Key, Value) and (Key = Name) then
      Result := I;
end;

function GetConfig(const Lines: TArrayOfString; const Name: String): String;
var
  Index: Integer;
  Key: String;
begin
  Result := '';
  Index := FindConfig(Lines, Name);
  if Index >= 0 then
    ParseLine(Lines[Index], Key, Result);
end;

{ Sets the value of the configuration with the provided name, keeping
  any other configuration (eg: added by hand), an empty value removes
  the configuration so that the default value of the node is used }
procedure SetConfig(var Lines: TArrayOfString; const Name, Value: String);
var
  I, Index, Count: Integer;
begin
  Index := FindConfig(Lines, Name);
  Count := GetArrayLength(Lines);
  if Value = '' then
  begin
    if Index < 0 then
      Exit;
    for I := Index to Count - 2 do
      Lines[I] := Lines[I + 1];
    SetArrayLength(Lines, Count - 1);
  end
  else if Index >= 0 then
    Lines[Index] := ConfigLine(Name, Value)
  else
  begin
    SetArrayLength(Lines, Count + 1);
    Lines[Count] := ConfigLine(Name, Value);
  end;
end;

{ Retrieves the initial value of a field, the parameters of the command
  line take precedence over the configuration file provided with the
  /CONFIG parameter, that takes precedence over the existing configuration }
function InitialValue(const Param, Name, Default: String): String;
begin
  Result := ExpandConstant('{param:' + Param + '|}');
  if Result = '' then
    Result := GetConfig(ParamConfig, Name);
  if Result = '' then
    Result := GetConfig(Config, Name);
  if Result = '' then
    Result := Default;
end;

{ Converts the provided name into an identifier that is valid in the
  URLs of the server (lower cased letters and digits separated by dashes) }
function Slugify(const Value: String): String;
var
  I: Integer;
  Lower: String;
  Dash: Boolean;
begin
  Result := '';
  Dash := False;
  Lower := Lowercase(Value);
  for I := 1 to Length(Lower) do
    if ((Lower[I] >= 'a') and (Lower[I] <= 'z')) or
      ((Lower[I] >= '0') and (Lower[I] <= '9')) then
    begin
      if Dash and (Result <> '') then
        Result := Result + '-';
      Dash := False;
      Result := Result + Lower[I];
    end
    else
      Dash := True;
  if Result = '' then
    Result := 'node';
end;

{ Verifies if the provided (explicit) node identifier is valid in the URLs
  of the server, starting with a letter or a digit, followed by letters,
  digits, dashes, underscores and dots }
function ValidNodeId(const Id: String): Boolean;
var
  I: Integer;
begin
  Result := Id <> '';
  for I := 1 to Length(Id) do
    if not (((Id[I] >= 'a') and (Id[I] <= 'z')) or ((Id[I] >= 'A') and (Id[I] <= 'Z')) or
      ((Id[I] >= '0') and (Id[I] <= '9')) or ((I > 1) and (Pos(Id[I], '-_.') > 0))) then
      Result := False;
end;

function NormalizeUrl(Url: String): String;
begin
  Result := Trim(Url);
  if (Result <> '') and (Result[Length(Result)] <> '/') then
    Result := Result + '/';
end;

function ValidUrl(const Url: String): Boolean;
begin
  Result := (Pos('http://', Lowercase(Url)) = 1) or (Pos('https://', Lowercase(Url)) = 1);
end;

{ Extracts the (lower cased) host of the provided URL, keeping the brackets
  of the IPv6 addresses, so that it can be compared with the local ones }
function UrlHost(const Url: String): String;
var
  Index: Integer;
begin
  Result := Lowercase(Url);
  Index := Pos('://', Result);
  if Index > 0 then
    Result := Copy(Result, Index + 3, Length(Result));
  Index := Pos('/', Result);
  if Index > 0 then
    Result := Copy(Result, 1, Index - 1);
  Index := Pos('@', Result);
  if Index > 0 then
    Result := Copy(Result, Index + 1, Length(Result));
  if (Result <> '') and (Result[1] = '[') then
    Index := Pos(']', Result) + 1
  else
    Index := Pos(':', Result);
  if Index > 1 then
    Result := Copy(Result, 1, Index - 1);
end;

{ Verifies if the provided URL is secure for the node, either because it
  uses HTTPS or because it targets the local machine (loopback), as the
  secret key is sent to the server }
function SecureUrl(const Url: String): Boolean;
var
  Host: String;
  I: Integer;
begin
  Result := Pos('https://', Lowercase(Url)) = 1;
  if Result then
    Exit;
  Host := UrlHost(Url);
  Result := (Host = 'localhost') or (Host = '[::1]');
  if Result or (Pos('127.', Host) <> 1) then
    Exit;
  Result := True;
  for I := 1 to Length(Host) do
    if not (((Host[I] >= '0') and (Host[I] <= '9')) or (Host[I] = '.')) then
      Result := False;
end;

#ifdef XP
function ConvertStringSecurityDescriptorToSecurityDescriptor(Descriptor: String;
  Revision: Cardinal; var SecurityDescriptor: Longint; Size: Longint): BOOL;
  external 'ConvertStringSecurityDescriptorToSecurityDescriptorW@advapi32.dll stdcall';

function SetFileSecurity(FileName: String; Information: Cardinal;
  SecurityDescriptor: Longint): BOOL;
  external 'SetFileSecurityW@advapi32.dll stdcall';

function LocalFree(Memory: Longint): Longint;
  external 'LocalFree@kernel32.dll stdcall';

function GetVolumeInformation(RootPath: String; Name: Longint; NameSize: Cardinal;
  var Serial, Component, Flags: Cardinal; FileSystem: Longint;
  FileSystemSize: Cardinal): BOOL;
  external 'GetVolumeInformationW@kernel32.dll stdcall';

{ The owner and the access of a file (or directory) can't be verified in the
  Windows XP nodes, as PowerShell is not part of Windows XP, so that no file
  (or directory) is trusted, meaning that only the data directory of an
  installed node (restricted by the installer) is used, any other one (eg:
  the one kept by an uninstall) being removed as an untrusted one }
function TrustedPath(const Path: String): Boolean;
begin
  Log('Owner and access of ' + Path + ' not verified');
  Result := False;
end;

{ Restricts the access to the provided directory (and to the contents created
  in it) to the system account and to the administrators, that become its
  owners, returning if it succeeded, the security functions of Windows are
  used (with a security descriptor that identifies the accounts by their well
  known identifiers) as Windows XP has no icacls and its cacls requires the
  names of the accounts (and an answer) in the language of Windows, notice
  that it's not possible in the volumes without security (eg: FAT32) }
function RestrictDir(const Path: String): Boolean;
var
  Descriptor: Longint;
begin
  Result := False;
  if ConvertStringSecurityDescriptorToSecurityDescriptor(
    'O:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)', 1, Descriptor, 0) then
  begin
    if SetFileSecurity(Path, 5, Descriptor) then
      Result := True;
    LocalFree(Descriptor);
  end;
  if not Result then
    Log('Could not restrict the access to ' + Path);
end;

{ Verifies if the volume of the provided path supports the security of its
  files (access control lists), which is not the case of the FAT32 ones, a
  volume whose information can't be retrieved is considered to support it,
  so that a failure to restrict the access to its files is never ignored }
function SecureVolume(const Path: String): Boolean;
var
  Serial, Component, Flags: Cardinal;
begin
  Result := True;
  if GetVolumeInformation(AddBackslash(ExtractFileDrive(Path)), 0, 0, Serial,
    Component, Flags, 0, 0) then
    Result := (Flags and 8) <> 0;
end;

{ Verifies if the registry has application paths of Python 2.7 (for the
  machine or for the system account), the directories (eg: added by another
  program) where Python always searches for its modules before its own
  library, which can't be disabled in the Python of the Windows XP nodes }
function ApplicationPaths: Boolean;
var
  Names: TArrayOfString;
begin
  Result := (RegGetSubkeyNames(HKLM, 'SOFTWARE\Python\PythonCore\2.7\PythonPath', Names) and
    (GetArrayLength(Names) > 0)) or
    (RegGetSubkeyNames(HKU, 'S-1-5-18\Software\Python\PythonCore\2.7\PythonPath', Names) and
    (GetArrayLength(Names) > 0));
end;

{ Runs NSSM (the service wrapper of the Windows XP nodes) with the provided
  parameters, returning if it succeeded }
function Nssm(const Params: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{app}\nssm.exe'), Params, '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

{ Configures the service of the node with the values of the configuration
  file of WinSW (service.xml), as NSSM is configured with commands, the node
  is run without a console, as NSSM is not able to create it in the current
  versions of Windows, and the paths of the parameters are quoted (with the
  quotes escaped) as they contain spaces, notice that the rotated log files
  are not removed and that the path of the wrapper is quoted in the service,
  as NSSM registers it without quotes, which would allow another program
  (eg: C:\Program.exe) to be run by the service as the system account, the
  node is told (through its environment) to restart itself by exiting, as
  NSSM starts it again and (unlike WinSW) is not detected by the node }
function ConfigureService: Boolean;
var
  Prefix, Logs: String;
  ResultCode: Integer;
begin
  Prefix := 'set ' + ServiceName + ' ';
  Logs := DataDir + '\logs\' + ServiceName;
  Result := Exec(ExpandConstant('{sys}\sc.exe'), 'config ' + ServiceName + ' binPath= "\"' +
    ExpandConstant('{app}\nssm.exe') + '\""', '', SW_HIDE, ewWaitUntilTerminated,
    ResultCode) and (ResultCode = 0) and
    Nssm(Prefix + 'DisplayName {#AppName}') and
    Nssm(Prefix + 'Description Receives the print jobs of the Colony Print server ' +
      'and prints them on the printers of this machine, updating itself from PyPI ' +
      'whenever it starts.') and
    Nssm(Prefix + 'Application "' + ExpandConstant('{app}\python\python.exe') + '"') and
    Nssm(Prefix + 'AppParameters -E -s -u "\"' + ExpandConstant('{app}\boot.py') +
      '\"" --config "\"' + ConfigPath + '\""') and
    Nssm(Prefix + 'AppDirectory "' + DataDir + '"') and
    Nssm(Prefix + 'AppEnvironmentExtra NODE_RESTART=exit') and
    Nssm(Prefix + 'AppStdout "' + Logs + '.out.log"') and
    Nssm(Prefix + 'AppStderr "' + Logs + '.err.log"') and
    Nssm(Prefix + 'AppRotateFiles 1') and
    Nssm(Prefix + 'AppRotateOnline 1') and
    Nssm(Prefix + 'AppRotateBytes 10485760') and
    Nssm(Prefix + 'AppNoConsole 1') and
    Nssm(Prefix + 'AppRestartDelay 10000') and
    Nssm(Prefix + 'DependOnService Spooler');
end;
#else
{ Verifies if the provided file (or directory) can be trusted, meaning that
  only the system account and the administrators own it and have access to it
  (as the data directory restricted by the installer), as one created by any
  other user (eg: before the node was installed) or that grants access to any
  other user can't be trusted, the owner and the access are retrieved by
  PowerShell (as Inno Setup has no way of retrieving them) directly with .NET,
  so that no module is loaded (eg: the one of another PowerShell in the module
  path), the access to them being denied also makes it untrusted, notice that
  only two distinct exit codes are accepted and that the verification fails
  (raising) otherwise, so that a verification that didn't run (eg: blocked
  PowerShell) never causes the removal of the data directory }
function TrustedPath(const Path: String): Boolean;
var
  Kind: String;
  ResultCode: Integer;
begin
  if DirExists(Path) then
    Kind := 'Directory'
  else
    Kind := 'File';
  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -Command "try { $a = [System.IO.' + Kind +
    ']::GetAccessControl(''' + Path + '''); $t = @(''S-1-5-18'', ''S-1-5-32-544''); ' +
    '$s = [System.Security.Principal.SecurityIdentifier]; ' +
    'if ($a.GetOwner($s).Value -notin $t) { exit 65 }; ' +
    'foreach ($r in $a.GetAccessRules($true, $true, $s)) { ' +
    'if ($r.IdentityReference.Value -notin $t) { exit 65 } }; exit 64 } catch { ' +
    'if ($_.Exception.GetBaseException() -is [System.UnauthorizedAccessException]) ' +
    '{ exit 65 }; exit 1 }"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or
    ((ResultCode <> 64) and (ResultCode <> 65)) then
    RaiseException('Could not verify the owner and the access of ' + Path +
      ' (code ' + IntToStr(ResultCode) + ')');
  Log('Owner and access of ' + Path + ' verified with code ' + IntToStr(ResultCode));
  Result := ResultCode = 64;
end;

{ Runs icacls with the provided parameters, returning if it succeeded }
function Icacls(const Params: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\icacls.exe'), Params, '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;
#endif

{ Removes a data directory that was not created by the installer (it's not
  trusted), taking its ownership and resetting its access first, as its
  creator may have denied the access to the administrators, so that its
  contents (eg: a configuration pointing to other packages) are never used,
  notice that its ownership is not taken (nor its access reset) in the
  Windows XP nodes, that are not able to do it for its contents }
function RemoveUntrustedDataDir: Boolean;
begin
  Log('Removing the untrusted data directory ' + DataDir);
#ifndef XP
  Icacls('"' + DataDir + '" /setowner *S-1-5-32-544 /T /C /Q');
  Icacls('"' + DataDir + '" /reset /T /C /Q');
#endif
  DelTree(DataDir, True, True, True);
  Result := not DirExists(DataDir);
end;

{ Creates the data directory with its access already restricted to the system
  account and to the administrators, by restricting it in the program files
  (where the users can't create anything) and then moving it into place, in
  the same volume, which fails in case the data directory exists (eg: created
  by another user meanwhile), so that no other user ever has access to it
  (not even for an instant), notice that its access is reset first, so that
  only the restricted access is kept, and that in the Windows XP nodes it's
  created without being restricted in the volumes without security (FAT32) }
function CreateDataDir: Boolean;
var
  TempDir: String;
begin
  Result := False;
  Log('Creating the data directory ' + DataDir);
  TempDir := ExpandConstant('{#ProgramFiles}\{#AppName}.data');
  if DirExists(TempDir) then
    DelTree(TempDir, True, True, True);
  if not CreateDir(TempDir) then
    Exit;
#ifdef XP
  if not RestrictDir(TempDir) and SecureVolume(TempDir) then
    Exit;
#else
  if not Icacls('"' + TempDir + '" /reset /C /Q') then
    Exit;
  if not Icacls('"' + TempDir + '" /inheritance:r /grant:r *S-1-5-18:(OI)(CI)F ' +
    '*S-1-5-32-544:(OI)(CI)F') then
    Exit;
  if not Icacls('"' + TempDir + '" /setowner *S-1-5-32-544 /C /Q') then
    Exit;
#endif
  Result := RenameFile(TempDir, DataDir);
  if not Result then
  begin
    Log('Could not move ' + TempDir + ' to ' + DataDir);
    DelTree(TempDir, True, True, True);
  end;
end;

function ServiceExists: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\sc.exe'), 'query ' + ServiceName, '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

{ Retrieves the path to the wrapper (image) of the existing service, without
  its quotes and arguments, empty in case there's no service }
function ServiceImage: String;
var
  Index: Integer;
begin
  Result := '';
  if not RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Services\' + ServiceName,
    'ImagePath', Result) then
    Exit;
  Result := Trim(Result);
  if (Result <> '') and (Result[1] = '"') then
  begin
    Result := Copy(Result, 2, Length(Result));
    Index := Pos('"', Result) - 1;
  end
  else
    Index := Pos('.exe', Lowercase(Result)) + 3;
  if Index > 3 then
    Result := Copy(Result, 1, Index);
end;

{ Verifies if the existing service is the one of this installer, the one
  whose wrapper is in its directory, as the installer of the Windows XP nodes
  and the one of the other nodes use the same service name with different
  wrappers in different directories, the short names of the directories are
  compared, so that the same directory is never taken as another one }
function OwnService: Boolean;
begin
  Result := CompareText(GetShortName(ExtractFilePath(ServiceImage)),
    GetShortName(AddBackslash(ExpandConstant('{app}')))) = 0;
end;

{ Retrieves the directory where the other installer (the one of the Windows
  XP nodes or the one of the other nodes) installs its node, the program files
  of the other architecture, empty in case there's none (32 bit Windows) }
function OtherDir: String;
begin
  Result := '';
#ifdef XP
  if IsWin64 then
    Result := ExpandConstant('{pf64}\{#AppName}');
#else
  Result := ExpandConstant('{commonpf32}\{#AppName}');
#endif
end;

{ Removes the node of the other installer, whose service would otherwise be
  kept instead of the one of this installer, by running its uninstaller, that
  removes its service and its files while keeping its configuration, and
  waiting for the service to be removed (as the uninstaller returns before
  it's done), notice that the uninstaller is only run when the wrapper of the
  service is in the directory of the other installer, so that no other program
  is ever run, the service is deleted in case it's not the one of the other
  installer (or its uninstaller fails), returning if it was removed }
function RemoveOtherNode: Boolean;
var
  Uninstaller: String;
  ResultCode, I: Integer;
begin
  Log('Removing the ' + ServiceName + ' service of another installer');
  Uninstaller := AddBackslash(OtherDir) + 'unins000.exe';
  if (OtherDir <> '') and (CompareText(GetShortName(ExtractFilePath(ServiceImage)),
    GetShortName(AddBackslash(OtherDir))) = 0) and FileExists(Uninstaller) then
  begin
    Exec(Uninstaller, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
    for I := 1 to 60 do
    begin
      if not ServiceExists then
        Break;
      Sleep(1000);
    end;
  end;
  if ServiceExists then
    Exec(ExpandConstant('{sys}\sc.exe'), 'delete ' + ServiceName, '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
  Result := not ServiceExists;
end;

{ Retrieves the default printer of the user running the installer, as the
  service runs under the system account, which has no default printer }
function UserDefaultPrinter: String;
var
  Device: String;
  Index: Integer;
begin
  Result := '';
  if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows NT\CurrentVersion\Windows',
    'Device', Device) then
  begin
    Index := Pos(',', Device);
    if Index > 0 then
      Result := Copy(Device, 1, Index - 1)
    else
      Result := Device;
  end;
end;

function EmailMode: Boolean;
begin
  Result := ModePage.SelectedValueIndex = 1;
end;

function NodeId: String;
begin
  Result := InitialValue('ID', 'NODE_ID', '');
  if Result = '' then
    Result := Slugify(Trim(NodePage.Values[0]));
end;

{ Verifies that the server is reachable and accepts the secret key, by
  listing its nodes (an operation that requires the secret key), notice
  that the installer of the Windows XP nodes doesn't verify a server that
  uses HTTPS in the versions of Windows older than 8.1, as their HTTP client
  doesn't enable (by default) the secure protocols (TLS 1.2) required by the
  current servers, which are supported by the Python of the node }
function TestServer(const Url, Key: String; var Message: String): Boolean;
var
  Request: Variant;
begin
  Result := False;
#ifdef XP
  if (Pos('https://', Lowercase(Url)) = 1) and (GetWindowsVersion < $06030000) then
  begin
    Log('Server not verified, as this version of Windows lacks its secure protocols');
    Result := True;
    Exit;
  end;
#endif
  try
    Request := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    Request.SetTimeouts(10000, 10000, 15000, 15000);
    Request.Open('GET', Url + 'nodes', False);
    Request.SetRequestHeader('X-Secret-Key', Key);
    Request.Send('');
    if Request.Status = 200 then
      Result := True
    else if (Request.Status = 401) or (Request.Status = 403) then
      Message := 'The server rejected the secret key (HTTP ' + IntToStr(Request.Status) + ').'
    else
      Message := 'The server replied with HTTP ' + IntToStr(Request.Status) + '.';
  except
    Message := 'Could not reach the server: ' + GetExceptionMessage;
  end;
end;

function ValidateServer: String;
begin
  Result := '';
  if not ValidUrl(ServerPage.Values[0]) then
    Result := 'The server URL must start with http:// or https://.'
  else if Trim(ServerPage.Values[1]) = '' then
    Result := 'The secret key of the server must be provided.';
end;

function ValidateNode: String;
begin
  Result := '';
  if Trim(NodePage.Values[0]) = '' then
    Result := 'The name of the node must be provided.'
  else if not ValidNodeId(NodeId) then
    Result := 'The identifier of the node (' + NodeId + '), from the /ID parameter ' +
      'or from the existing configuration, must only have letters, digits, dashes, ' +
      'underscores and dots.';
end;

function ValidateEmail: String;
begin
  Result := '';
  if not EmailMode then
    Exit;
  if Trim(EmailPage.Values[0]) = '' then
    Result := 'The email receivers must be provided in email mode.'
  else if Trim(EmailPage.Values[1]) = '' then
    Result := 'The Mailme key must be provided in email mode.';
end;

{ Loads the configuration of the existing data directory, only when it can
  be trusted, either because the service is installed (as the data directory
  is restricted before the service is installed) or because only the system
  account and the administrators own it and have access to it, as a data
  directory or configuration created by any other user (eg: before the node
  was installed) can't be trusted, notice that the untrusted data directory
  is only removed once the installation starts and that the setup is aborted
  in case it can't be verified }
function InitializeSetup: Boolean;
var
  Trusted: Boolean;
begin
  Result := True;
  Trusted := False;
  try
    if FileExists(ConfigPath) then
    begin
      if ServiceExists then
        Trusted := True
      else if TrustedPath(DataDir) then
        Trusted := TrustedPath(ConfigPath);
      if Trusted then
        LoadStringsFromFile(ConfigPath, Config)
      else
        Log('Ignoring the untrusted configuration file ' + ConfigPath);
    end;
  except
    Log(GetExceptionMessage);
    SuppressibleMsgBox(GetExceptionMessage, mbCriticalError, MB_OK, IDOK);
    Result := False;
  end;
end;

procedure InitializeWizard;
var
  Mode, ParamPath: String;
begin
  ParamPath := ExpandConstant('{param:CONFIG|}');
  if ParamPath <> '' then
    if not LoadStringsFromFile(ParamPath, ParamConfig) then
      Log('Could not load the configuration file ' + ParamPath);
  DetectedPrinter := UserDefaultPrinter;

  ServerPage := CreateInputQueryPage(wpSelectDir, 'Server',
    'Colony Print server of the node',
    'Enter the URL of the Colony Print server and the secret key the node uses ' +
    'to authenticate with it.');
  ServerPage.Add('Server URL:', False);
  ServerPage.Add('Secret key:', True);
  ServerPage.Values[0] := InitialValue('URL', 'BASE_URL', DefaultUrl);
  ServerPage.Values[1] := InitialValue('KEY', 'SECRET_KEY', '');

  ModePage := CreateInputOptionPage(ServerPage.ID, 'Mode',
    'How the node handles its print jobs',
    'Choose how the print jobs received by this node are handled.', True, False);
  ModePage.Add('Normal - print the jobs on the printers of this machine');
  ModePage.Add('Email - print the jobs to PDF files and send them by email');
  Mode := Lowercase(InitialValue('MODE', 'NODE_MODE', 'normal'));
  if Mode = 'email' then
    ModePage.SelectedValueIndex := 1
  else
    ModePage.SelectedValueIndex := 0;

  NodePage := CreateInputQueryPage(ModePage.ID, 'Node',
    'Identification of this node',
    'The name and the location identify this node in the Colony Print server. ' +
    'The printer is used by the jobs that do not select one, as the service ' +
    'runs under the system account, which has no default printer.');
  NodePage.Add('Name:', False);
  NodePage.Add('Location (optional):', False);
  NodePage.Add('Printer:', False);
  NodePage.Values[0] := InitialValue('NAME', 'NODE_NAME', GetComputerNameString);
  NodePage.Values[1] := InitialValue('LOCATION', 'NODE_LOCATION', '');
  NodePage.Values[2] := InitialValue('PRINTER', 'NODE_PRINTER', DetectedPrinter);

  EmailPage := CreateInputQueryPage(NodePage.ID, 'Email',
    'Delivery of the generated PDF files',
    'The PDF files of the print jobs are sent to the email receivers using ' +
    'the Mailme service.');
  EmailPage.Add('Email receivers (separated by ;):', False);
  EmailPage.Add('Mailme key:', True);
  EmailPage.Add('Mailme URL (optional):', False);
  EmailPage.Values[0] := InitialValue('EMAILS', 'NODE_EMAIL_RECEIVERS', '');
  EmailPage.Values[1] := InitialValue('MAILMEKEY', 'MAILME_KEY', '');
  EmailPage.Values[2] := InitialValue('MAILMEURL', 'MAILME_BASE_URL', '');
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  { suggests the PDF printer in email mode (the jobs are printed to PDF
    files) and the default printer of the user in normal mode }
  if CurPageID = NodePage.ID then
  begin
    if EmailMode and ((NodePage.Values[2] = '') or (NodePage.Values[2] = DetectedPrinter)) then
      NodePage.Values[2] := PdfPrinter
    else if not EmailMode and (NodePage.Values[2] = PdfPrinter) then
      NodePage.Values[2] := DetectedPrinter;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = EmailPage.ID) and not EmailMode;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Message: String;
begin
  Result := True;
  if CurPageID = ServerPage.ID then
  begin
    ServerPage.Values[0] := NormalizeUrl(ServerPage.Values[0]);
    Message := ValidateServer;
    if Message <> '' then
    begin
      SuppressibleMsgBox(Message, mbError, MB_OK, IDOK);
      Result := False;
    end
    else if not SecureUrl(ServerPage.Values[0]) and (SuppressibleMsgBox(
      'The server URL does not use HTTPS, so the secret key is sent ' +
      'unencrypted.' + #13#10#13#10 + 'Continue with this server URL anyway?',
      mbConfirmation, MB_YESNO, IDYES) <> IDYES) then
      Result := False
    else if not TestServer(ServerPage.Values[0], Trim(ServerPage.Values[1]), Message) then
    begin
      { silent installs continue, as the server may not be reachable
        while installing (eg: when preparing the machine elsewhere) }
      Log(Message);
      Result := SuppressibleMsgBox(Message + #13#10#13#10 +
        'Continue with this server configuration anyway?', mbConfirmation, MB_YESNO,
        IDYES) = IDYES;
    end;
  end
  else if CurPageID = NodePage.ID then
  begin
    Message := ValidateNode;
    if Message <> '' then
    begin
      SuppressibleMsgBox(Message, mbError, MB_OK, IDOK);
      Result := False;
    end
    else if Trim(NodePage.Values[2]) = '' then
      Result := SuppressibleMsgBox('Without a printer the jobs that do not select one ' +
        'fail, as the system account has no default printer.' + #13#10#13#10 +
        'Continue without a printer?', mbConfirmation, MB_YESNO, IDYES) = IDYES;
  end
  else if CurPageID = EmailPage.ID then
  begin
    Message := ValidateEmail;
    if Message <> '' then
    begin
      SuppressibleMsgBox(Message, mbError, MB_OK, IDOK);
      Result := False;
    end;
  end;
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  Mode: String;
begin
  if EmailMode then
    Mode := 'email'
  else
    Mode := 'normal';
  Result := MemoDirInfo + NewLine + NewLine +
    'Server:' + NewLine + Space + ServerPage.Values[0] + NewLine + NewLine +
    'Node:' + NewLine +
    Space + 'Name: ' + Trim(NodePage.Values[0]) + NewLine +
    Space + 'Identifier: ' + NodeId + NewLine +
    Space + 'Location: ' + Trim(NodePage.Values[1]) + NewLine +
    Space + 'Printer: ' + Trim(NodePage.Values[2]) + NewLine +
    Space + 'Mode: ' + Mode;
  if EmailMode then
    Result := Result + NewLine + Space + 'Email receivers: ' + Trim(EmailPage.Values[0]);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  Trusted: Boolean;
begin
  { the node is only installed under the program files, where the users
    can't change anything, as the service runs its files (eg: the boot
    script and the Python interpreter) as the system account }
  if Pos(Lowercase(AddBackslash(ExpandConstant('{#ProgramFiles}'))),
    Lowercase(AddBackslash(ExpandFileName(ExpandConstant('{app}'))))) <> 1 then
  begin
    Result := 'The node must be installed in ' + ExpandConstant('{#ProgramFiles}') + '.';
    Exit;
  end;

#ifdef XP
  { warns that the node can't be protected in the volumes without security
    (eg: FAT32), where any user is able to read the secret key and to change
    the files run by the service (as the system account), silent installs
    continue, as the machines are prepared by their administrators }
  if not SecureVolume(ExpandConstant('{app}')) or not SecureVolume(DataDir) then
    if SuppressibleMsgBox('The disk of this machine has no file security (eg: FAT32), ' +
      'so any user of this machine is able to read the secret key of the server ' +
      'and to change the files of the node, that run as the system account.' + #13#10#13#10 +
      'Continue with the installation anyway?', mbConfirmation, MB_YESNO, IDYES) <> IDYES then
    begin
      Result := 'The node was not installed, as its disk has no file security.';
      Exit;
    end;

  { warns that the modules of the node may be loaded from other directories,
    the application paths of Python 2.7 in the registry, so that any user
    able to write in them is able to run code as the system account, silent
    installs continue, as the machines are prepared by their administrators }
  if ApplicationPaths then
    if SuppressibleMsgBox('The registry of this machine has application paths of Python 2.7 ' +
      '(eg: added by another program), where the node also searches for its modules, so ' +
      'any user able to write in them is able to run code as the system account.' + #13#10#13#10 +
      'Continue with the installation anyway?', mbConfirmation, MB_YESNO, IDYES) <> IDYES then
    begin
      Result := 'The node was not installed, as Python 2.7 has application paths.';
      Exit;
    end;
#endif

  { validates the configuration once more, as the pages are not
    shown (and so not validated) when running silently }
  ServerPage.Values[0] := NormalizeUrl(ServerPage.Values[0]);
  Result := ValidateServer;
  if Result = '' then
    Result := ValidateNode;
  if Result = '' then
    Result := ValidateEmail;
  if Result <> '' then
    Exit;

  { verifies the data directory (once more) now that the installation starts,
    as it may have been created by another user since the setup started,
    removing it when it's not trusted, and creates it (restricted) unless
    it was verified, which fails (aborting the setup) in case it appeared
    meanwhile, so that only a data directory created by the installer (or
    one that was verified) is ever used }
  Trusted := ServiceExists;
  if not Trusted and DirExists(DataDir) then
  begin
    try
      Trusted := TrustedPath(DataDir);
      if not Trusted then
        if not RemoveUntrustedDataDir then
          Result := 'Could not remove the untrusted data directory ' + DataDir + '.';
    except
      Result := GetExceptionMessage + '.';
    end;
    if Result <> '' then
      Exit;
  end;
  { a file in the place of the data directory (that any user may create in
    the program data) is removed, as it would make its creation fail }
  if FileExists(DataDir) then
  begin
    Log('Removing the file in the place of the data directory ' + DataDir);
#ifndef XP
    Icacls('"' + DataDir + '" /setowner *S-1-5-32-544 /C /Q');
    Icacls('"' + DataDir + '" /reset /C /Q');
#endif
    DeleteFile(DataDir);
  end;
  if not Trusted or not DirExists(DataDir) then
    if not CreateDataDir then
    begin
      Result := 'Could not create the data directory ' + DataDir + '.';
      Exit;
    end;

  { stops the service of a previous installation, so that its files
    (eg: the Python interpreter) can be replaced }
  if ServiceExists then
  begin
    Log('Stopping the ' + ServiceName + ' service');
    Exec(ExpandConstant('{sys}\net.exe'), 'stop ' + ServiceName, '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
  end;

  { removes the node of the other installer (the one of the Windows XP
    nodes or the one of the other nodes), so that this one replaces it,
    notice that its configuration is kept (it was already loaded) }
  if ServiceExists and not OwnService then
    if not RemoveOtherNode then
      Result := 'Could not remove the ' + ServiceName + ' service of another installer.';
end;

procedure WriteConfig;
var
  Lines: TArrayOfString;
  I: Integer;
  Id, Mode: String;
begin
  Id := NodeId;
  SetArrayLength(Lines, GetArrayLength(Config));
  for I := 0 to GetArrayLength(Config) - 1 do
    Lines[I] := Config[I];
  if EmailMode then
    Mode := 'email'
  else
    Mode := 'normal';
  SetConfig(Lines, 'BASE_URL', ServerPage.Values[0]);
  SetConfig(Lines, 'SECRET_KEY', Trim(ServerPage.Values[1]));
  SetConfig(Lines, 'NODE_ID', Id);
  SetConfig(Lines, 'NODE_NAME', Trim(NodePage.Values[0]));
  SetConfig(Lines, 'NODE_LOCATION', Trim(NodePage.Values[1]));
  SetConfig(Lines, 'NODE_PRINTER', Trim(NodePage.Values[2]));
  SetConfig(Lines, 'NODE_MODE', Mode);
  SetConfig(Lines, 'NODE_EMAIL_RECEIVERS', Trim(EmailPage.Values[0]));
  SetConfig(Lines, 'MAILME_KEY', Trim(EmailPage.Values[1]));
  SetConfig(Lines, 'MAILME_BASE_URL', Trim(EmailPage.Values[2]));
  if not SaveStringsToUTF8File(ConfigPath, Lines, False) then
    RaiseException('Could not write the configuration file ' + ConfigPath);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep <> ssPostInstall then
    Exit;

  { restricts the access to the data directory (that contains the secret
    key and the configuration of the service) to the system account
    and to the administrators, before writing the configuration to it, and
    takes the ownership and resets the access of its contents, so that the
    files created while it was open (since its creation) are not kept, notice
    that only the data directory is restricted in the Windows XP nodes, its
    contents inheriting its access, which is only allowed to fail in the
    volumes without security (FAT32), after the warning of the installer }
#ifdef XP
  if not RestrictDir(DataDir) and SecureVolume(DataDir) then
    RaiseException('Could not restrict the access to ' + DataDir);
#else
  if not Icacls('"' + DataDir + '" /inheritance:r /grant:r *S-1-5-18:(OI)(CI)F ' +
    '*S-1-5-32-544:(OI)(CI)F') then
    RaiseException('Could not restrict the access to ' + DataDir);
  Icacls('"' + DataDir + '" /setowner *S-1-5-32-544 /T /C /Q');
  Icacls('"' + DataDir + '\*" /reset /T /C /Q');
#endif

  { writes the configuration and takes its ownership, as a (new) file is
    owned by the user running the installer (unless the policy makes the
    administrators the owners), that is not trusted by the next install }
  WriteConfig;
#ifndef XP
  Icacls('"' + ConfigPath + '" /setowner *S-1-5-32-544 /C /Q');
#endif

#ifdef XP
  { installs the runtime of the Python of the Windows XP nodes (Visual C++
    2008), that is not part of that Python nor of Windows XP, so that the
    node is not able to start without it, notice that an already installed
    runtime and a required restart are not failures, and that a failure
    doesn't prevent the service from being installed and started, as the
    runtime may already be installed (eg: by a previous install) }
  Log('Installing the Visual C++ 2008 runtime');
  if not Exec(ExpandConstant('{tmp}\vcredist_x86.exe'), '/q', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) or ((ResultCode <> 0) and
    (ResultCode <> 1638) and (ResultCode <> 3010)) then
  begin
    ServiceError := True;
    Log('Could not install the Visual C++ 2008 runtime (code ' + IntToStr(ResultCode) + ')');
    SuppressibleMsgBox('The Visual C++ 2008 runtime, required by the node, could not ' +
      'be installed (code ' + IntToStr(ResultCode) + ').', mbError, MB_OK, IDOK);
  end;
#endif

  { installs the service, the one of the Windows XP nodes (NSSM) being
    configured on every install, as it has no configuration file }
  if not ServiceExists then
  begin
    Log('Installing the ' + ServiceName + ' service');
#ifdef XP
    if not Exec(ExpandConstant('{app}\nssm.exe'), 'install ' + ServiceName + ' "' +
      ExpandConstant('{app}\python\python.exe') + '"', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
#else
    if not Exec(ExpandConstant('{app}\' + ServiceName + '.exe'), 'install', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
#endif
    begin
      ServiceError := True;
      Log('Could not install the service (code ' + IntToStr(ResultCode) + ')');
      SuppressibleMsgBox('The ' + ServiceName + ' service could not be installed (code ' +
        IntToStr(ResultCode) + ').', mbError, MB_OK, IDOK);
      Exit;
    end;
  end;
#ifdef XP
  if not ConfigureService then
  begin
    ServiceError := True;
    Log('Could not configure the service');
    SuppressibleMsgBox('The ' + ServiceName + ' service could not be configured.',
      mbError, MB_OK, IDOK);
    Exit;
  end;
#endif

  Log('Starting the ' + ServiceName + ' service');
  if not Exec(ExpandConstant('{sys}\net.exe'), 'start ' + ServiceName, '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
  begin
    ServiceError := True;
    Log('Could not start the service (code ' + IntToStr(ResultCode) + ')');
    SuppressibleMsgBox('The ' + ServiceName + ' service could not be started (code ' +
      IntToStr(ResultCode) + '), check the logs in ' + DataDir + '\logs.',
      mbError, MB_OK, IDOK);
  end;
end;

{ Makes the installer return a (custom) error exit code in case the
  service could not be installed or started, so that the failure is
  noticed by unattended (silent) installations }
function GetCustomSetupExitCode: Integer;
begin
  Result := 0;
  if ServiceError then
    Result := 10;
end;
