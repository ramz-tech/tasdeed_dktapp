; NSIS Script for Tasdeed ORION App Installer

Name "Tasdeed ORION App"
OutFile "TasdeedORIONppInstaller.exe"
InstallDir "$PROGRAMFILES64\TasdeedORIONApp"
SetCompress off
RequestExecutionLevel admin

!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\main.exe"
!define MUI_FINISHPAGE_RUNTEXT "Launch Tasdeed ORION App"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "Install"

  ; Welcome Message
  DetailPrint "Welcome to the Tasdeed ORION App Installer!"

  ; Create Installation Directory
  DetailPrint "Setting up installation directory..."
  CreateDirectory "$INSTDIR"

  ; Copy Application Files
  DetailPrint "Copying application files to $INSTDIR..."
  SetOutPath "$INSTDIR"
  File /r "C:\Users\Dell\Desktop\tasdeed_dktapp\dist\*.*"

  ; Install Playwright Dependencies
  DetailPrint "Installing Playwright dependencies. This may take a while..."
  ExecWait '"$INSTDIR\python.exe" -m pip install playwright > $INSTDIR\install_log.txt' $0
  IfErrors 0 +2
    MessageBox MB_OK "Error: Failed to install Playwright. Check install_log.txt for details."

  ExecWait '"$INSTDIR\python.exe" -m playwright install >> $INSTDIR\install_log.txt' $1
  IfErrors 0 +2
    MessageBox MB_OK "Error: Failed to install Playwright browsers. Check install_log.txt for details."

  ; Set Environment Variable for Playwright Browsers
  DetailPrint "Setting up environment variables..."
  WriteRegStr HKCU "Environment" "PLAYWRIGHT_BROWSERS_PATH" "$INSTDIR\playwright-browsers"
  System::Call 'Kernel32::SendMessageTimeout(i 0xffff, i 0x001A, i 0, t "Environment", i 0x0002, i 5000, *i .r0)'

  ; Install Shortcuts
  DetailPrint "Creating shortcuts..."
  CreateShortcut "$DESKTOP\Tasdeed ORION App.lnk" "$INSTDIR\main.exe" "" "$INSTDIR\icon.ico" 0
  CreateShortcut "$SMPROGRAMS\Tasdeed ORION App\Tasdeed ORION App.lnk" "$INSTDIR\main.exe" "" "$INSTDIR\icon.ico" 0

  ; Write Uninstaller
  DetailPrint "Setting up uninstaller..."
  WriteUninstaller "$INSTDIR\uninstall.exe"

  DetailPrint "Installation complete! Click Finish to launch the app."

SectionEnd

Section "Uninstall"

  ; Goodbye Message
  DetailPrint "Uninstalling Tasdeed ORION App..."

  ; Remove Files and Shortcuts
  Delete "$INSTDIR\*.*"
  Delete "$DESKTOP\Tasdeed ORION App.lnk"
  Delete "$SMPROGRAMS\Tasdeed ORION App\Tasdeed ORION App.lnk"

  ; Remove Directory
  RMDir "$INSTDIR"

  DetailPrint "Tasdeed ORION App has been successfully uninstalled."

SectionEnd
