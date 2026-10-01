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

[Setup]
AppId={{08AC6285-8BAA-453D-8EF4-72F19B392ED3}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Hive Solutions Lda.
AppPublisherURL=https://github.com/hivesolutions/colony-print
AppSupportURL=https://github.com/hivesolutions/colony-print/issues
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=admin
CloseApplications=no
OutputDir={#OutputDir}
OutputBaseFilename=colony-print-node-setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\python\python.exe
VersionInfoVersion={#AppVersion}

[InstallDelete]
; removes the previous Python installation (including the packages installed
; by the self-update) so that no stale package is left behind
Type: filesandordirs; Name: "{app}\python"

[Files]
Source: "{#BuildDir}\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#BuildDir}\{#ServiceName}.exe"; DestDir: "{app}"; Flags: ignoreversion
; the boot script is run from a copy outside of the packages updated by it,
; so that an interrupted (or broken) update never prevents the service from
; starting and updating the packages once more
Source: "{#BuildDir}\boot.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "service.xml"; DestDir: "{app}"; DestName: "{#ServiceName}.xml"; Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\{#AppName}"
Name: "{commonappdata}\{#AppName}\logs"

[UninstallRun]
Filename: "{sys}\net.exe"; Parameters: "stop {#ServiceName}"; Flags: runhidden waituntilterminated; RunOnceId: "StopService"
Filename: "{app}\{#ServiceName}.exe"; Parameters: "uninstall"; Flags: runhidden waituntilterminated; RunOnceId: "DeleteService"

[UninstallDelete]
; the configuration and the logs of the node are kept, so that they're
; reused in case the node is installed again
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{commonappdata}\{#AppName}\packages"

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
    Value := Copy(Value, 2, Length(Value) - 2);
  Result := True;
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
    Lines[Index] := Name + '=' + Value
  else
  begin
    SetArrayLength(Lines, Count + 1);
    Lines[Count] := Name + '=' + Value;
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
  secret key is sent to the server and the packages installed by the
  service are retrieved from it (only through HTTPS, by default) }
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

{ Verifies if the provided file (or directory) is owned by the system account
  or by the administrators, the only ones allowed to write the data directory
  of the node, as one created by any other user (eg: before the node was
  installed) can't be trusted, notice that only a distinct exit code (and not
  a failure or a PowerShell that runs nothing) is considered as trusted, as
  Inno Setup has no way of retrieving the owner }
function TrustedOwner(const Path: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -Command "if ((Get-Acl -LiteralPath ''' + Path +
    ''').GetOwner([System.Security.Principal.SecurityIdentifier]).Value -in ' +
    '@(''S-1-5-18'', ''S-1-5-32-544'')) { exit 64 } else { exit 1 }"', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) and (ResultCode = 64);
end;

{ Runs icacls with the provided parameters, returning if it succeeded }
function Icacls(const Params: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\icacls.exe'), Params, '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

{ Removes a data directory that was not created by the installer (its owner
  is not trusted), taking its ownership and resetting its access first, as
  its creator may have denied the access to the administrators, so that its
  contents (eg: a configuration pointing to other packages) are never used }
procedure RemoveUntrustedDataDir;
begin
  Log('Removing the untrusted data directory ' + DataDir);
  Icacls('"' + DataDir + '" /setowner *S-1-5-32-544 /T /C /Q');
  Icacls('"' + DataDir + '" /reset /T /C /Q');
  if not DelTree(DataDir, True, True, True) then
    RaiseException('Could not remove the untrusted data directory ' + DataDir);
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
  listing its nodes (an operation that requires the secret key) }
function TestServer(const Url, Key: String; var Message: String): Boolean;
var
  Request: Variant;
begin
  Result := False;
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
    Result := 'The name of the node must be provided.';
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

procedure InitializeWizard;
var
  Mode, ParamPath: String;
begin
  { only the configuration written by the installer (or by the system and
    administrators) is used, as a data directory or configuration created
    by any other user (eg: before the node was installed) can't be trusted }
  if DirExists(DataDir) and not TrustedOwner(DataDir) then
    RemoveUntrustedDataDir;
  if FileExists(ConfigPath) then
  begin
    if TrustedOwner(ConfigPath) then
      LoadStringsFromFile(ConfigPath, Config)
    else
      Log('Ignoring the untrusted configuration file ' + ConfigPath);
  end;
  ParamPath := ExpandConstant('{param:CONFIG|}');
  if ParamPath <> '' then
    if not LoadStringsFromFile(ParamPath, ParamConfig) then
      Log('Could not load the configuration file ' + ParamPath);
  DetectedPrinter := UserDefaultPrinter;

  ServerPage := CreateInputQueryPage(wpSelectDir, 'Server',
    'Colony Print server of the node',
    'Enter the URL of the Colony Print server and the secret key the node uses ' +
    'to authenticate with it. The node also updates itself from this server.');
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
      'The server URL does not use HTTPS, so the secret key is sent unencrypted ' +
      'and the node does not update itself from the server (unless the insecure ' +
      'update is allowed with NODE_UPDATE_INSECURE=1).' + #13#10#13#10 +
      'Continue with this server URL anyway?', mbConfirmation, MB_YESNO,
      IDYES) <> IDYES) then
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

function ServiceExists: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\sc.exe'), 'query ' + ServiceName, '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
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

  { stops the service of a previous installation, so that its files
    (eg: the Python interpreter) can be replaced }
  if ServiceExists then
  begin
    Log('Stopping the ' + ServiceName + ' service');
    Exec(ExpandConstant('{sys}\net.exe'), 'stop ' + ServiceName, '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
  end;
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
    key and the packages installed by the service) to the system account
    and to the administrators, before writing the configuration to it, and
    takes the ownership and resets the access of its contents, so that the
    files created while it was open (since its creation) are not kept }
  if not Icacls('"' + DataDir + '" /inheritance:r /grant:r *S-1-5-18:(OI)(CI)F ' +
    '*S-1-5-32-544:(OI)(CI)F') then
    RaiseException('Could not restrict the access to ' + DataDir);
  Icacls('"' + DataDir + '" /setowner *S-1-5-32-544 /T /C /Q');
  Icacls('"' + DataDir + '\*" /reset /T /C /Q');
  WriteConfig;

  if not ServiceExists then
  begin
    Log('Installing the ' + ServiceName + ' service');
    if not Exec(ExpandConstant('{app}\' + ServiceName + '.exe'), 'install', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    begin
      ServiceError := True;
      Log('Could not install the service (code ' + IntToStr(ResultCode) + ')');
      SuppressibleMsgBox('The ' + ServiceName + ' service could not be installed (code ' +
        IntToStr(ResultCode) + ').', mbError, MB_OK, IDOK);
      Exit;
    end;
  end;

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
