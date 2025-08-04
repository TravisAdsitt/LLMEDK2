## How to Add a Menu Item to the OVMF BIOS Menu

The OVMF firmware uses the UEFI HII (Human Interface Infrastructure) system to create and manage BIOS setup menus. Here's how you can add a new menu item:

### 1. **Understanding the Current Menu Structure**

OVMF's BIOS menu is primarily implemented through:
- **UiApp** (`MdeModulePkg/Application/UiApp/`) - Main front page application
- **PlatformDxe** (`OvmfPkg/PlatformDxe/`) - Platform-specific configuration options
- **SetupBrowser** (`MdeModulePkg/Universal/SetupBrowserDxe/`) - HII form browser engine

### 2. **Two Main Approaches**

#### **Approach A: Add to Existing Platform Configuration**

Modify the existing PlatformDxe module to add your menu item:

1. **Update the VFR file** (`OvmfPkg/PlatformDxe/PlatformForms.vfr`):
```vfr
// Add your new menu item after the existing ones
checkbox
  varid      = MainFormState.YourNewOption,
  questionid = QUESTION_YOUR_NEW_OPTION,
  prompt     = STRING_TOKEN(STR_YOUR_NEW_OPTION),
  help       = STRING_TOKEN(STR_YOUR_NEW_OPTION_HELP),
  flags      = CHECKBOX_DEFAULT,
endcheckbox;
```

2. **Update the form state structure** in `Platform.h`:
```c
typedef struct {
  CHAR16  CurrentPreferredResolution[MAXSIZE_RES_CUR];
  UINT32  NextPreferredResolution;
  BOOLEAN YourNewOption;  // Add your new field
} MAIN_FORM_STATE;
```

3. **Add string tokens** in `Platform.uni`:
```
#string STR_YOUR_NEW_OPTION      #language en-US "Your New Option"
#string STR_YOUR_NEW_OPTION_HELP #language en-US "Help text for your option"
```

4. **Handle the callback** in `Platform.c`:
```c
// In the Callback function, add a new case:
case QUESTION_YOUR_NEW_OPTION:
  // Handle your option logic here
  break;
```

#### **Approach B: Create a New HII Driver**

Create a completely new DXE driver that provides HII forms:

1. **Create a new driver directory** (e.g., `OvmfPkg/YourMenuDxe/`)

2. **Create the INF file** (`YourMenuDxe.inf`):
```ini
[Defines]
  INF_VERSION                    = 0x00010005
  BASE_NAME                      = YourMenuDxe
  FILE_GUID                      = [Generate new GUID]
  MODULE_TYPE                    = DXE_DRIVER
  VERSION_STRING                 = 1.0
  ENTRY_POINT                    = YourMenuInit

[Sources]
  YourMenu.c
  YourMenu.h
  YourMenuVfr.vfr
  YourMenuStrings.uni

[Packages]
  MdePkg/MdePkg.dec
  MdeModulePkg/MdeModulePkg.dec
  OvmfPkg/OvmfPkg.dec

[LibraryClasses]
  UefiDriverEntryPoint
  UefiBootServicesTableLib
  HiiLib
  DebugLib

[Protocols]
  gEfiHiiConfigAccessProtocolGuid
  gEfiDevicePathProtocolGuid

[Guids]
  gEfiIfrTianoGuid
```

3. **Create the VFR file** (`YourMenuVfr.vfr`):
```vfr
#define FORMSET_GUID  { 0x12345678, 0x1234, 0x5678, 0x90, 0xab, 0xcd, 0xef, 0x12, 0x34, 0x56, 0x78 }

formset
  guid     = FORMSET_GUID,
  title    = STRING_TOKEN(STR_FORMSET_TITLE),
  help     = STRING_TOKEN(STR_FORMSET_HELP),
  classguid = EFI_HII_PLATFORM_SETUP_FORMSET_GUID,

  form formid = 1,
       title  = STRING_TOKEN(STR_FORM_TITLE);

    checkbox
      varid      = YourFormState.EnableFeature,
      questionid = 0x1000,
      prompt     = STRING_TOKEN(STR_ENABLE_FEATURE),
      help       = STRING_TOKEN(STR_ENABLE_FEATURE_HELP),
      flags      = CHECKBOX_DEFAULT,
    endcheckbox;

  endform;
endformset;
```

4. **Implement the driver** (`YourMenu.c`):
```c
#include <Uefi.h>
#include <Protocol/HiiConfigAccess.h>
#include <Library/UefiDriverEntryPoint.h>
#include <Library/HiiLib.h>
// ... other includes

EFI_STATUS
EFIAPI
YourMenuInit (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  EFI_STATUS Status;

  // Install HII Config Access Protocol
  // Register HII packages
  // Set up form handling

  return EFI_SUCCESS;
}
```

5. **Add to the build** by updating `OvmfPkg/OvmfPkgX64.dsc`:
```ini
[Components]
  # ... existing components
  OvmfPkg/YourMenuDxe/YourMenuDxe.inf
```

### 3. **Key Concepts to Understand**

- **HII Forms**: Use VFR (Visual Forms Representation) language to define UI elements
- **Config Access Protocol**: Handles form data extraction, routing, and callbacks
- **String Packages**: Store localized strings for the UI
- **Form State**: Binary data structure that holds form values
- **Question IDs**: Unique identifiers for form elements that trigger callbacks

### 4. **Testing Your Changes**

1. Build OVMF with your changes
2. Boot a VM with the new OVMF firmware
3. Access the setup menu (usually F2 or Delete during boot)
4. Navigate to your new menu item

### 5. **Important Notes**

- The `classguid = EFI_HII_PLATFORM_SETUP_FORMSET_GUID` in your VFR makes the form appear in the main setup browser
- Use the `UiListThirdPartyDrivers` function in UiApp to automatically discover and display your HII forms
- Handle form callbacks properly to process user input and save configuration
- Consider persistent storage for your configuration data using UEFI variables

**SOURCES:**
- `MdeModulePkg/Application/UiApp/FrontPage.c`
- `MdeModulePkg/Application/UiApp/FrontPageVfr.Vfr`
- `MdeModulePkg/Application/UiApp/FrontPageCustomizedUi.c`
- `MdeModulePkg/Application/UiApp/FrontPageCustomizedUiSupport.c`
- `OvmfPkg/PlatformDxe/Platform.c`
- `OvmfPkg/PlatformDxe/PlatformForms.vfr`
- `MdeModulePkg/Universal/SetupBrowserDxe/Setup.c`
- `OvmfPkg/OvmfPkgX64.dsc`
------------------------------------------------------------