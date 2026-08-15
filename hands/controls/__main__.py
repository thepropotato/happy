"""WHAT EVERY CONTROL SAYS RIGHT NOW: python -m hands.controls"""

from hands.controls import clipboard, display, network, power, volume

charge = power.battery().splitlines()

print(f"sound      {volume.status()}")
print(f"brightness {display.status()}")
print(f"battery    {charge[0] if charge else '?'}")
print(f"network    {network.status().splitlines()[0]}")
print(f"clipboard  {clipboard.read()[:60].strip()}")
