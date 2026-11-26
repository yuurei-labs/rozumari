# RP2 default modules
include("$(PORT_DIR)/boards/manifest.py")

# Asyncio
require("asyncio")

# WiFi / networking / ntptime
require("bundle-networking")

# Bluetooth LE
require("aioble")

# Rozumari firmware
freeze("$(PORT_DIR)/modules")
