"""THE VOLUME AND THE MUTE SWITCH."""

from hands.controls.commands import (
    REFUSED,
    UNSUPPORTED,
    clamp,
    number,
    on_mac,
    on_windows,
    osascript,
    powershell,
)

MAC_READ = (
    "set now to get volume settings\n"
    'return (output volume of now as string) & " " & (output muted of now as string)'
)

# WINDOWS HAS NO COMMAND FOR THE VOLUME, SO THE AUDIO ENDPOINT IS ADDRESSED
# DIRECTLY. THE UNNAMED METHODS ARE PLACEHOLDERS: THE ORDER IS THE INTERFACE.
WINDOWS_SHIM = """
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {
  int a(); int b(); int c(); int d();
  int SetMasterVolumeLevelScalar(float level, System.Guid context);
  int e();
  int GetMasterVolumeLevelScalar(out float level);
  int f(); int g(); int h(); int i();
  int SetMute([MarshalAs(UnmanagedType.Bool)] bool mute, System.Guid context);
  int GetMute(out bool mute);
}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {
  int Activate(ref System.Guid id, int context, int parameters, out IAudioEndpointVolume volume);
}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {
  int a();
  int GetDefaultAudioEndpoint(int flow, int role, out IMMDevice device);
}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class Enumerator { }
public class Sound {
  static IAudioEndpointVolume Endpoint() {
    IMMDeviceEnumerator found = new Enumerator() as IMMDeviceEnumerator;
    IMMDevice device; Marshal.ThrowExceptionForHR(found.GetDefaultAudioEndpoint(0, 1, out device));
    IAudioEndpointVolume volume; System.Guid id = typeof(IAudioEndpointVolume).GUID;
    Marshal.ThrowExceptionForHR(device.Activate(ref id, 23, 0, out volume));
    return volume;
  }
  public static float Level {
    get { float level; Marshal.ThrowExceptionForHR(Endpoint().GetMasterVolumeLevelScalar(out level)); return level; }
    set { Marshal.ThrowExceptionForHR(Endpoint().SetMasterVolumeLevelScalar(value, System.Guid.Empty)); }
  }
  public static bool Muted {
    get { bool muted; Marshal.ThrowExceptionForHR(Endpoint().GetMute(out muted)); return muted; }
    set { Marshal.ThrowExceptionForHR(Endpoint().SetMute(value, System.Guid.Empty)); }
  }
}
'@ -ErrorAction SilentlyContinue
"""


def status():
    if on_mac():
        said = osascript(MAC_READ)

        if said is None:
            return "I could not read the sound settings."

        level, _, muted = said.partition(" ")

        return f"The volume is {level} percent{' and it is muted' if 'true' in muted else ''}."

    if on_windows():
        said = powershell(WINDOWS_SHIM + '"$([int]([Sound]::Level * 100)) $([Sound]::Muted)"')

        if said is None:
            return "I could not read the sound settings."

        level, _, muted = said.partition(" ")

        return f"The volume is {level} percent{' and it is muted' if 'True' in muted else ''}."

    return UNSUPPORTED


def level():
    """THE VOLUME AS A NUMBER OUT OF A HUNDRED, OR None."""
    if on_mac():
        return number(osascript("output volume of (get volume settings)"))

    if on_windows():
        return number(powershell(WINDOWS_SHIM + "[int]([Sound]::Level * 100)"))

    return None


def set_level(wanted):
    value = clamp(wanted)

    if value is None:
        return "The volume has to be a number between zero and one hundred."

    if on_mac():
        done = osascript(f"set volume output volume {value}")
    elif on_windows():
        done = powershell(WINDOWS_SHIM + f"[Sound]::Level = {value / 100}")
    else:
        return UNSUPPORTED

    return f"Volume set to {value} percent." if done is not None else REFUSED


def change(step):
    now = level()

    if now is None:
        return "I could not read the volume." if on_mac() or on_windows() else UNSUPPORTED

    return set_level(now + step)


def mute(on):
    if on_mac():
        done = osascript(f"set volume output muted {'true' if on else 'false'}")
    elif on_windows():
        done = powershell(WINDOWS_SHIM + f"[Sound]::Muted = ${str(bool(on)).lower()}")
    else:
        return UNSUPPORTED

    if done is None:
        return REFUSED

    return "Sound muted." if on else "Sound unmuted."
