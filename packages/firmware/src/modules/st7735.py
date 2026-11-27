import time
from math import sqrt

from machine import SPI, Pin

from lib.constants import FONT, LCD_CS, LCD_DC, LCD_RS, LCD_SCK, LCD_SDA
from lib.singleton import Singleton
from lib.utils import Utils

Rotations = [0x00, 0x60, 0xC0, 0xA0]  # 0, 90, 180, 270 degrees

BGR = 0x08
RGB = 0x00

utils = Utils()


class ST7735(Singleton):
    def __init__(self, size: tuple[int, int] = (128, 160)):
        """Initialize the ST7735 display driver.

        Configures the SPI interface, control pins, display dimensions, rotation,
        color mode, and internal drawing buffers.

        Args:
            size: Initial display dimensions as (width, height), in pixels.
        """
        self.spi = SPI(
            1,
            baudrate=20_000_000,
            polarity=0,
            phase=0,
            sck=Pin(LCD_SCK),
            mosi=Pin(LCD_SDA),
            miso=None,
        )
        self.dc = Pin(LCD_DC, Pin.OUT)
        self.rs = Pin(LCD_RS, Pin.OUT)
        self.cs = Pin(LCD_CS, Pin.OUT)
        self.cs.value(1)

        self._size = size
        self._offset = bytearray([0, 0])
        self._rotate = 0
        self._rgb = True
        self._tfa = 0
        self._bfa = 0

        self._color_data = bytearray(2)
        self._window_loc_data = bytearray(4)

        self._buf = bytes(self._color_data) * 32

    def size(self) -> tuple[int, int]:
        """Get the current logical display dimensions.

        Returns:
            Display dimensions as (width, height), in pixels.
        """
        return self._size

    def active(self, on: bool = True) -> None:
        """Turn display output on or off.

        Args:
            on: True to enable display output, or False to disable it.
        """
        self._cmd(ST7735.DISPON if on else ST7735.DISPOFF)

    def invert(self, invert: bool = True):
        """Enable or disable display color inversion.

        Args:
            invert: True to invert colors, or False to use normal colors.
        """
        self._cmd(ST7735.INVON if invert else ST7735.INVOFF)

    def rgb_mode(self, rgb: bool = True) -> None:
        """Set the display pixel color order.

        Updates the MADCTL register to select RGB or BGR color ordering.

        Args:
            rgb: True to use RGB order, or False to use BGR order.
        """
        self._rgb = rgb
        self._set_MADCTL()

    def rotation(self, rotate: int) -> None:
        """Set the display orientation.

        Updates the display rotation and swaps logical width and height when
        changing between portrait and landscape orientations.

        Args:
            rotate: Rotation index: 0 for 0°, 1 for 90°, 2 for 180°,
                or 3 for 270°.
        """
        if 0 <= rotate <= 3:
            root_change = self._rotate ^ rotate
            self._rotate = rotate

            if root_change & 1:
                self._size = (self._size[1], self._size[0])
            self._set_MADCTL()

    def pixel(self, pos: tuple[int, int], color: int) -> None:
        """Draw a single pixel at the specified coordinate.

        Args:
            pos: Pixel coordinate as (x, y).
            color: Pixel color in 16-bit RGB565 format.
        """
        if 0 <= pos[0] < self._size[0] and 0 <= pos[1] < self._size[1]:
            self._set_window_point(pos)
            self._pushcolor(color)

    def text(
        self,
        *,
        pos: tuple[int, int],
        text: str,
        color: int,
        size: tuple[int, int] | int = 1,
        wrap: bool = False,
        center: bool = False,
    ) -> None:
        """Render text on the display using the configured font.

        Supports horizontal centering, custom scaling, and optional line
        wrapping when text reaches the display boundary.

        Args:
            pos: Starting coordinate as (x, y).
            text: String to render.
            color: Text color in 16-bit RGB565 format.
            size: Uniform scaling factor or (horizontal, vertical) scaling.
            wrap: Whether to continue rendering on the next line when the
                text reaches the display boundary.
            center: Whether to center the text horizontally on the display.
        """
        if isinstance(size, int):
            wh = (size, size)
        else:
            wh = size

        orig_x, y = pos
        font_width = FONT["width"]
        width = wh[0] * font_width + 1

        if center:
            total_text_width = (len(text) - 1) * width + (wh[0] * font_width)
            x = (self._size[0] - total_text_width) // 2
            x = max(0, x)

            start_x = x
        else:
            x = orig_x
            start_x = orig_x

        for char in text:
            self.char(pos=(x, y), char=char, color=color, sizes=wh)
            x += width

            if x + width > self._size[0]:
                if wrap:
                    y += FONT["height"] * wh[1] + 1
                    x = start_x
                else:
                    break

    def char(
        self,
        *,
        pos: tuple[int, int],
        char: str,
        color: int,
        sizes: tuple[int, int] = (1, 1),
    ) -> None:
        """Render a single character using the configured font.

        Creates a scaled pixel buffer for the character and draws it at
        the specified display coordinate.

        Args:
            pos: Top-left coordinate as (x, y).
            char: Character to render.
            color: Character color in 16-bit RGB565 format.
            sizes: Horizontal and vertical scaling factors.
        """
        start_char = FONT["start"]
        end_char = FONT["end"]
        ci = ord(char)

        if start_char <= ci <= end_char:
            font_width = FONT["width"]
            font_height = FONT["height"]
            ci = (ci - start_char) * font_width
            char_data = FONT["data"][ci : ci + font_width]

            w = font_width * sizes[0]
            h = font_height * sizes[1]

            buf = bytearray(w * h * 2)

            ch = color >> 8
            cl = color & 0xFF

            for x_idx, c in enumerate(char_data):
                for y_idx in range(font_height):
                    if c & 0x01:
                        for sx in range(sizes[0]):
                            for sy in range(sizes[1]):
                                px = x_idx * sizes[0] + sx
                                py = y_idx * sizes[1] + sy
                                idx = (py * w + px) * 2
                                buf[idx] = ch
                                buf[idx + 1] = cl
                    c >>= 1

            x0, y0 = pos
            x1 = x0 + w - 1
            y1 = y0 + h - 1

            self.image(x0=x0, y0=y0, x1=x1, y1=y1, data=buf)

    def blit(self, *, x: int, y: int, w: int, h: int, data: bytearray) -> None:
        """Draw a raw pixel buffer within a rectangular display region.

        Args:
            x: Left coordinate of the region.
            y: Top coordinate of the region.
            w: Region width in pixels.
            h: Region height in pixels.
            data: Pixel buffer containing RGB565 color data.
        """
        self.image(x0=x, y0=y, x1=x + w - 1, y1=y + h - 1, data=data)

    def line(self, *, start: tuple[int, int], end: tuple[int, int], color: int):
        """Draw a line between two coordinates.

        Uses optimized horizontal and vertical line drawing for axis-aligned
        lines and an incremental line algorithm for diagonal lines.

        Args:
            start: Starting coordinate as (x, y).
            end: Ending coordinate as (x, y).
            color: Line color in 16-bit RGB565 format.
        """
        if start[0] == end[0]:
            pnt = end if (end[1] < start[1]) else start
            self.vline(pos=pnt, length=abs(end[1] - start[1]) + 1, color=color)
        elif start[1] == end[1]:
            pnt = end if end[0] < start[0] else start
            self.hline(pos=pnt, length=abs(end[0] - start[0]) + 1, color=color)
        else:
            sx, sy = start
            ex, ey = end

            dx = ex - sx
            dy = ey - sy

            inx = 1 if dx > 0 else -1
            iny = 1 if dy > 0 else -1
            dx = abs(dx)
            dy = abs(dy)

            if dx >= dy:
                dy <<= 1
                e = dy - dx
                dx <<= 1

                while sx != ex:
                    self.pixel((sx, sy), color)
                    if e >= 0:
                        sy += iny
                        e -= dx
                    e += dy
                    sx += inx
            else:
                dx <<= 1
                e = dx - dy
                dy <<= 1

                while sy != ey:
                    self.pixel((sx, sy), color)
                    if e >= 0:
                        sx += inx
                        e -= dy
                    e += dx
                    sy += iny

    def vline(self, *, pos: tuple[int, int], length: int, color: int) -> None:
        """Draw a vertical line.

        Args:
            pos: Starting coordinate as (x, y).
            length: Line length in pixels.
            color: Line color in 16-bit RGB565 format.
        """
        x, y = pos

        start = (
            utils.clamp(x, 0, self._size[0]),
            utils.clamp(y, 0, self._size[1]),
        )
        stop = start[0], utils.clamp(start[1] + length, 0, self._size[1])

        if stop[1] < start[1]:
            start, stop = stop, start

        self._set_window_loc(start, stop)
        self._set_color(color)
        self._draw(length)

    def hline(self, *, pos: tuple[int, int], length: int, color: int) -> None:
        """Draw a horizontal line.

        Args:
            pos: Starting coordinate as (x, y).
            length: Line length in pixels.
            color: Line color in 16-bit RGB565 format.
        """
        x, y = pos

        start = utils.clamp(x, 0, self._size[0]), utils.clamp(y, 0, self._size[1])
        stop = utils.clamp(start[0] + length, 0, self._size[0]), start[1]

        if stop[0] < start[0]:
            start, stop = stop, start

        self._set_window_loc(start, stop)
        self._set_color(color)
        self._draw(length)

    def rect(self, *, pos: tuple[int, int], size: tuple[int, int], color: int) -> None:
        """Draw an unfilled rectangle outline.

        Args:
            pos: Top-left coordinate as (x, y).
            size: Rectangle dimensions as (width, height).
            color: Outline color in 16-bit RGB565 format.
        """
        self.hline(pos=pos, length=size[0], color=color)
        self.hline(pos=(pos[0], pos[1] + size[1] - 1), length=size[0], color=color)

        self.vline(pos=pos, length=size[1], color=color)
        self.vline(pos=(pos[0] + size[0] - 1, pos[1]), length=size[1], color=color)

    def fill_rect(
        self, *, pos: tuple[int, int], size: tuple[int, int], color: int
    ) -> None:
        """Draw a filled rectangle.

        Args:
            pos: Top-left coordinate as (x, y).
            size: Rectangle dimensions as (width, height).
            color: Fill color in 16-bit RGB565 format.
        """
        start = (
            utils.clamp(pos[0], 0, self._size[0]),
            utils.clamp(pos[1], 0, self._size[1]),
        )
        end = (
            utils.clamp(start[0] + size[0] - 1, 0, self._size[0]),
            utils.clamp(start[1] + size[1] - 1, 0, self._size[1]),
        )

        if end[0] < start[0]:
            tmp = end[0]
            end = (start[0], end[1])
            start = (tmp, start[1])
        if end[1] < start[1]:
            tmp = end[1]
            end = (end[0], start[1])
            start = (start[0], tmp)

        self._set_window_loc(start, end)
        pixels = (end[0] - start[0] + 1) * (end[1] - start[1] + 1)
        self._set_color(color)
        self._draw(pixels)

    def circle(self, *, pos: tuple[int, int], radius: int, color: int) -> None:
        """Draw an unfilled circle outline.

        Uses circle symmetry to calculate and draw the perimeter pixels.

        Args:
            pos: Circle center coordinate as (x, y).
            radius: Circle radius in pixels.
            color: Outline color in 16-bit RGB565 format.
        """
        self._color_data[0] = color >> 8
        self._color_data[1] = color

        xend = int(0.7071 * radius) + 1
        rsq = radius**2

        xp, yp, xn, yn, xyp, yxp, xyn, yxn = 0, 0, 0, 0, 0, 0, 0, 0
        for x in range(xend):
            y = int(sqrt(rsq - x * x))
            xp = pos[0] + x
            yp = pos[1] + y
            xn = pos[0] - x
            yn = pos[1] - y
            xyp = pos[0] + y
            yxp = pos[1] + x
            xyn = pos[0] - y
            yxn = pos[1] - x

        self._set_window_point((xp, yp))
        self._data(self._color_data)
        self._set_window_point((xp, yn))
        self._data(self._color_data)
        self._set_window_point((xn, yp))
        self._data(self._color_data)
        self._set_window_point((xn, yn))
        self._data(self._color_data)
        self._set_window_point((xyp, yxp))
        self._data(self._color_data)
        self._set_window_point((xyp, yxn))
        self._data(self._color_data)
        self._set_window_point((xyn, yxp))
        self._data(self._color_data)
        self._set_window_point((xyn, yxn))
        self._data(self._color_data)

    def fill_circle(self, *, pos: tuple[int, int], radius: int, color: int) -> None:
        """Draw a filled circle.

        Uses vertical scan lines to fill the circle interior.

        Args:
            pos: Circle center coordinate as (x, y).
            radius: Circle radius in pixels.
            color: Fill color in 16-bit RGB565 format.
        """
        self._color_data[0] = color >> 8
        self._color_data[1] = color

        rsq = radius**2
        for x in range(radius):
            y = int(sqrt(rsq - x * x))
            y0 = pos[1] - y
            ey = y0 + y * 2
            y0 = utils.clamp(y0, 0, self._size[1])
            ln = abs(ey - y0) + 1

            self.vline(pos=(pos[0] + x, y0), length=ln, color=color)
            self.vline(pos=(pos[0] - x, y0), length=ln, color=color)

    def fill(self, color: int) -> None:
        """Fill the entire display with a solid color.

        Args:
            color: Fill color in 16-bit RGB565 format.
        """
        self.fill_rect(pos=(0, 0), size=self._size, color=color)

    def image(self, *, x0: int, y0: int, x1: int, y1: int, data: bytearray) -> None:
        """Draw a raw pixel buffer within the specified rectangular region.

        Args:
            x0: Left boundary coordinate.
            y0: Top boundary coordinate.
            x1: Right boundary coordinate.
            y1: Bottom boundary coordinate.
            data: Pixel buffer containing RGB565 color data.
        """
        self._set_window_loc((x0, y0), (x1, y1))
        self._data(data)

    def setvscroll(self, *, tfa: int, bfa: int) -> None:
        """Configure the display's vertical scrolling area.

        Defines the fixed top and bottom regions that remain unaffected
        by vertical scrolling.

        Args:
            tfa: Top fixed area height in pixels.
            bfa: Bottom fixed area height in pixels.
        """
        self._cmd(ST7735.VSCRDEF)

        data2 = bytearray([0, tfa])
        self._data(data2)

        data2[1] = 162 - tfa - bfa
        self._data(data2)

        data2[1] = bfa
        self._data(data2)

        self._tfa = tfa
        self._bfa = bfa

    def vscroll(self, value: int) -> None:
        """Set the vertical scroll position.

        Calculates the scroll start address while respecting the configured
        top and bottom fixed areas.

        Args:
            value: Vertical scroll offset in pixels.
        """
        a = value + self._tfa

        if a + self._bfa > 162:
            a = 162 - self._bfa

        self._vscrolladdr(a)

    def _vscrolladdr(self, addr: int) -> None:
        """Set the vertical scrolling start address.

        Writes the specified address to the display's vertical scroll
        start address register.

        Args:
            addr: Display memory line address.
        """
        self._cmd(ST7735.VSCSAD)
        data2 = bytearray([addr >> 8, addr & 0xFF])
        self._data(data2)

    def _set_color(self, color: int):
        """Prepare the internal color buffers for repeated pixel drawing.

        Converts the RGB565 color into two bytes and creates a reusable
        buffer containing repeated copies of that color.

        Args:
            color: Color value in 16-bit RGB565 format.
        """
        self._color_data[0] = color >> 8
        self._color_data[1] = color
        self._buf = bytes(self._color_data) * 32

    def _draw(self, pixels: int):
        """Write repeated color data to the display over SPI.

        Transmits the prepared color buffer for the requested number of
        pixels, followed by any remaining pixel data.

        Args:
            pixels: Number of pixels to draw.
        """
        self.dc.value(1)
        self.cs.value(0)

        for _ in range(pixels // 32):
            _ = self.spi.write(self._buf)

            rest = int(pixels) % 32
            if rest > 0:
                buf2 = bytes(self._color_data) * rest
                _ = self.spi.write(buf2)

        self.cs(1)

    def _cmd(self, cmd: int) -> None:
        """Send a command byte to the display over SPI.

        Sets the data/command pin to command mode before transmission.

        Args:
            cmd: Display controller command byte.
        """
        self.dc.value(0)
        self.cs.value(0)
        _ = self.spi.write(bytearray([cmd]))
        self.cs.value(1)

    def _data(self, data: bytearray) -> None:
        """Send data to the display over SPI.

        Sets the data/command pin to data mode before transmission.

        Args:
            data: Byte buffer containing the data to transmit.
        """
        self.dc.value(1)
        self.cs.value(0)
        _ = self.spi.write(data)
        self.cs.value(1)

    def _set_MADCTL(self) -> None:
        """Update the display Memory Data Access Control register.

        Applies the current rotation and RGB/BGR color order settings.
        """
        self._cmd(ST7735.MADCTL)
        rgb = RGB if self._rgb else BGR
        self._data(bytearray([Rotations[self._rotate] | rgb]))

    def _reset(self) -> None:
        """Perform a hardware reset of the display controller.

        Toggles the reset pin with the required delays between transitions.
        """
        self.rs.value(1)
        time.sleep(0.05)
        self.rs.value(0)
        time.sleep(0.05)
        self.rs.value(1)
        time.sleep(0.15)

    def _set_window_point(self, pos: tuple[int, int]) -> None:
        """Set the active display window to a single pixel.

        Applies display offsets and configures the column and row address
        registers before enabling memory write mode.

        Args:
            pos: Pixel coordinate as (x, y).
        """
        x = self._offset[0] + int(pos[0])
        y = self._offset[1] + int(pos[1])

        self._cmd(ST7735.CASET)
        self._window_loc_data[0] = x >> 8
        self._window_loc_data[1] = x & 0xFF
        self._window_loc_data[2] = x >> 8
        self._window_loc_data[3] = x & 0xFF
        self._data(self._window_loc_data)

        self._cmd(ST7735.RASET)
        self._window_loc_data[0] = y >> 8
        self._window_loc_data[1] = y & 0xFF
        self._window_loc_data[2] = y >> 8
        self._window_loc_data[3] = y & 0xFF
        self._data(self._window_loc_data)

        self._cmd(ST7735.RAMWR)

    def _set_window_loc(self, pos_0: tuple[int, int], pos_1: tuple[int, int]) -> None:
        """Set the active rectangular display window.

        Applies display offsets and configures the column and row address
        registers before enabling memory write mode.

        Args:
            pos_0: Top-left coordinate as (x, y).
            pos_1: Bottom-right coordinate as (x, y).
        """
        x0 = self._offset[0] + int(pos_0[0])
        x1 = self._offset[0] + int(pos_1[0])
        y0 = self._offset[1] + int(pos_0[1])
        y1 = self._offset[1] + int(pos_1[1])

        self._cmd(ST7735.CASET)
        self._window_loc_data[0] = x0 >> 8
        self._window_loc_data[1] = x0 & 0xFF
        self._window_loc_data[2] = x1 >> 8
        self._window_loc_data[3] = x1 & 0xFF
        self._data(self._window_loc_data)

        self._cmd(ST7735.RASET)
        self._window_loc_data[0] = y0 >> 8
        self._window_loc_data[1] = y0 & 0xFF
        self._window_loc_data[2] = y1 >> 8
        self._window_loc_data[3] = y1 & 0xFF
        self._data(self._window_loc_data)

        self._cmd(ST7735.RAMWR)

    def _pushcolor(self, color: int) -> None:
        """Write a single RGB565 color value to display memory.

        Args:
            color: Color value in 16-bit RGB565 format.
        """
        self._color_data[0] = color >> 8
        self._color_data[1] = color
        self._data(self._color_data)

    def init(self) -> None:
        """Initialize the display controller.

        Performs a hardware reset, exits sleep mode, configures frame timing,
        power control, color mode, orientation, and display output.
        """
        self._reset()

        self._cmd(ST7735.SWRESET)
        time.sleep(0.15)

        self._cmd(ST7735.SLPOUT)
        time.sleep(0.20)

        self._cmd(ST7735.FRMCTR1)
        self._data(bytearray([0x01, 0x2C, 0x2D]))

        self._cmd(ST7735.FRMCTR2)
        self._data(bytearray([0x01, 0x2C, 0x2D]))

        self._cmd(ST7735.FRMCTR3)
        self._data(bytearray([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D]))

        self._cmd(ST7735.INVCTR)
        self._data(bytearray([0x07]))

        self._cmd(ST7735.PWCTR1)  # Power control
        self._data(bytearray([0xA2, 0x02, 0x84]))

        self._cmd(ST7735.PWCTR2)
        self._data(bytearray([0xC5]))

        self._cmd(ST7735.PWCTR3)
        self._data(bytearray([0x0A, 0x00]))

        self._cmd(ST7735.PWCTR4)
        self._data(bytearray([0x8A, 0x2A]))

        self._cmd(ST7735.PWCTR5)
        self._data(bytearray([0x8A, 0xEE]))

        self._cmd(ST7735.VMCTR1)
        self._data(bytearray([0x0E]))

        self._cmd(ST7735.INVOFF)

        self._set_MADCTL()

        self._cmd(ST7735.COLMOD)
        self._data(bytearray([0x05]))

        self._cmd(ST7735.NORON)
        time.sleep(0.01)

        self._cmd(ST7735.DISPON)
        time.sleep(0.1)

        self.cs.value(1)

    def deinit(self) -> None:
        """Put the display into sleep mode.

        Sends the sleep-in command and releases the chip-select line.
        """
        self._cmd(ST7735.SLPIN)
        time.sleep(0.1)
        self.cs.value(1)

    NOP = 0x0

    SWRESET = 0x01
    RDDID = 0x04
    RDDST = 0x09

    SLPIN = 0x10
    SLPOUT = 0x11
    PTLON = 0x12
    NORON = 0x13

    INVOFF = 0x20
    INVON = 0x21
    DISPOFF = 0x28
    DISPON = 0x29
    CASET = 0x2A
    RASET = 0x2B
    RAMWR = 0x2C
    RAMRD = 0x2E

    VSCRDEF = 0x33
    VSCSAD = 0x37

    COLMOD = 0x3A
    MADCTL = 0x36

    FRMCTR1 = 0xB1
    FRMCTR2 = 0xB2
    FRMCTR3 = 0xB3
    INVCTR = 0xB4
    DISSET5 = 0xB6

    PWCTR1 = 0xC0
    PWCTR2 = 0xC1
    PWCTR3 = 0xC2
    PWCTR4 = 0xC3
    PWCTR5 = 0xC4
    VMCTR1 = 0xC5

    RDID1 = 0xDA
    RDID2 = 0xDB
    RDID3 = 0xDC
    RDID4 = 0xDD

    PWCTR6 = 0xFC

    GMCTRP1 = 0xE0
    GMCTRN1 = 0xE1

    BLACK = utils.rgb(0x00, 0x00, 0x00)
    RED = utils.rgb(0xFF, 0x00, 0x00)
    MAROON = utils.rgb(0x80, 0x00, 0x00)
    GREEN = utils.rgb(0x00, 0xFF, 0x00)
    FOREST = utils.rgb(0x00, 0x80, 0x80)
    BLUE = utils.rgb(0x00, 0x00, 0xFF)
    NAVY = utils.rgb(0x00, 0x00, 0x80)
    CYAN = utils.rgb(0x00, 0xFF, 0xFF)
    YELLOW = utils.rgb(0xFF, 0xFF, 0x00)
    PURPLE = utils.rgb(0xFF, 0x00, 0xFF)
    WHITE = utils.rgb(0xFF, 0xFF, 0xFF)
    GRAY = utils.rgb(0x80, 0x80, 0x80)
