; NSIS Script for tasdeed_dktapp Installer

; Define Installer Properties
Name "Tasdeed DKT App"
OutFile "TasdeedDKTAppInstaller.exe"
InstallDir "$PROGRAMFILES64\TasdeedDKTApp"
SetCompress off
RequestExecutionLevel admin

; Include Modern UI
!include "MUI2.nsh"

; Modern UI Settings
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; Installer Sections
Section "Install"

  ; Create Installation Directory
  CreateDirectory "$INSTDIR"

  ; Copy Application Files
  SetOutPath "$INSTDIR"
  File /r "path\to\your\application\*.*"

  ; Install Shortcuts
  CreateShortcut "$DESKTOP\TasdeedDKTApp.lnk" "$INSTDIR\main.exe"
  CreateShortcut "$SMPROGRAMS\TasdeedDKTApp\Uninstall.lnk" "$INSTDIR\uninstall.exe"

  ; Write Uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

; Uninstaller Section
Section "Uninstall"

  ; Remove Files and Shortcuts
  Delete "$INSTDIR\*.*"
  Delete "$DESKTOP\TasdeedDKTApp.lnk"
  Delete "$SMPROGRAMS\TasdeedDKTApp\Uninstall.lnk"

  ; Remove Directory
  RMDir "$INSTDIR"

SectionEnd
