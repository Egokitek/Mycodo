# coding=utf-8
import logging
import time

import Adafruit_SSD1306
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

logger = logging.getLogger("mycodo.device.lcd_pioled")


class LCD_Pioled:
    """Output to the PiOLED I2C LCD"""

    def __init__(self, lcd_dev):
        self.logger = logging.getLogger("mycodo.lcd_{id}".format(id=lcd_dev.unique_id.split('-')[0]))

        self.i2c_address = int(str(lcd_dev.location), 16)
        self.i2c_bus = lcd_dev.i2c_bus
        self.lcd_x_characters = lcd_dev.x_characters
        self.lcd_y_lines = lcd_dev.y_lines

        self.disp = Adafruit_SSD1306.SSD1306_128_32(
            rst=None,
            i2c_address=self.i2c_address,
            i2c_bus=self.i2c_bus)

        self.disp.begin()

    def lcd_init(self):
        """ Initialize LCD display """
        try:
            self.disp.clear()
            self.disp.display()
        except Exception as err:
            self.logger.error(
                "Could not initialize LCD. Check your configuration and wiring. Error: {err}".format(err=err))

    def lcd_write_lines(self,
                        message_line_1,
                        message_line_2,
                        message_line_3,
                        message_line_4):
        """ Send strings to display """
        x = 0
        top = -2  # padding
        font = ImageFont.load_default()

        image = Image.new('1', (self.disp.width, self.disp.height))

        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, self.disp.width, self.disp.height), outline=0, fill=0)

        draw.text((x, top), message_line_1, font=font, fill=255)
        draw.text((x, top + 8), message_line_2, font=font, fill=255)
        draw.text((x, top + 16), message_line_3, font=font, fill=255)
        draw.text((x, top + 25), message_line_4, font=font, fill=255)

        self.disp.image(image)
        self.disp.display()
        time.sleep(0.1)

    def lcd_backlight(self, state):
        """ backlight not supported """
        pass
