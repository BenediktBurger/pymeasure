#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2022 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging
from time import sleep
import re

import numpy as np

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import (
    truncated_discrete_set, strict_discrete_set,
    truncated_range
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class YokogawaAQ6370(Instrument):
    """
    Represents a Yokogawa AQ6370 class optical spectrum analyzer.

    Supported devices: AQ6370C/AQ6370D/AQ6373/AQ6373B/AQ6375/AQ6375B.
    IM AQ6370C-17EN    12th Edition
    """

    def __init__(self, resourceName, baud_rate=115200, port=10001, host="",
                 **kwargs):
        """Initialize the connection."""
        super().__init__(
            resourceName,
            "YokogawaAQ6370",
            asrl={'baud_rate': baud_rate,
                  'write_termination': "\r\n",
                  'read_termination': "\r\n"},
            tcpip={'host': host, 'port': port,
                   'write_termination': "\r\n",
                   'read_termination': "\r\n"},
        )
        if resourceName.startswith("TCPIP"):
            self.authenticate_ethernet(**kwargs)
        # Check the data type.
        self.config['data'] = self.query("FORMAT?")

    def authenticate_ethernet(self, username, password="", **kwargs):
        """Authenticate for an ethernet connection."""
        # TODO test
        # Open the connection. It has to be closed at the end.
        assert self.query(f'OPEN "{username}"') == "AUTHENTICATE CRAM-MD5."
        # Encrypted password transfer is possible.
        assert self.query(password) == "READY"
        self._ethernet = True

    def shutdown(self):
        """Close the connection if ethernet."""
        if self.adapter.startswith("TCPIP"):
            self.write("CLOSE")
        super().shutdown()

    id = Instrument.measurement(
        "*IDN?",
        """Get the identification of the device.

        Output: 'Manufacturer,Product,SerialNumber,FirmwareVersion'
        Sample: 'YOKOGAWA,AQ6370D,90Y403996,02.08' """
        )

    def clear(self):
        """Clear all event status registers."""
        self.write("*CLS")

    def reset(self):
        """Reset the instrument to default status."""
        self.write("*RST")

    status = Instrument.measurement(
        "*STB?", """Status byte of the device.""")

    # Sweep
    sweep_mode = Instrument.control(
        ":INITiate:SMODe?", ":INIT:SMOD %d",
        """The mode of the sweep: single,, repeat or auto.""",
        validator=truncated_discrete_set,
        values={"single": 1, "repeat": 2, "auto": 3},
        map_values=True
        )

    # Wavelength
    wavelength_center = Instrument.control(
        ":sens:wav:cent?", ":sens:wav:cent %s",
        """A settable property of the central wavelength of the sweep in m.
        You can set it with an exponential number or SI unit like 532nm.
        """)

    wavelength_automatic_center = Instrument.control(
        ":calc:mark:max:scenter:auto?", ":calc:mark:max:scenter:auto %s",
        """A settable boolean property whether the wavelength center follows
        the maximum""",
        validator=truncated_discrete_set,
        values={True: "ON", False: "OFF"},
        map_values=True
        )

    wavelength_start = Instrument.control(
        ":sens:wav:start?", ":sens:wav:start %s",
        """A settable property of the start wavelength of the sweep in m.
        You can set it with an exponential number or SI unit like 532nm.
        """)

    wavelength_staop = Instrument.control(
        ":sens:wav:stop?", ":sens:wav:stop %s",
        """A settable property of the stop wavelength of the sweep in m.
        You can set it with an exponential number or SI unit like 532nm.
        """)

    wavelength_span = Instrument.control(
        ":sens:wav:span?", ":sens:wav:span %s",
        """A settable property of the wavelength span of the sweep in m.
        You can set it with an exponential number or SI unit like 532nm.
        """)

    "Common Commands"

    def trigger(self):
        """Perform a single sweep according to previous conditions."""
        self.write("*TRG")  # "Trigger"

    "Device commands"

    def sweep(self):
        """Begin a sweep."""
        self.write(":INIT")

    def stop(self):
        """Abort a sweep."""
        self.write(":ABORT")

    # Wavelength
    def setWlCenter(self, wavelength):
        """Set the central wavelength in m or string including unit."""
        self.write(f":SENS:wav:cent {wavelength}")

    def setWlAutoCenter(self, auto=True):
        """Activate or deactivate the auto center."""
        self.write(f":calc:mark:max:scenter:auto {'ON' if auto else 'OFF'}")

    # Get Data
    def getTrace(self, axes="xy", trace="A", samples=None):
        """Get the data for trace from start sample to stop as a list."""
        if samples is None:
            area = ""
        else:
            area = f",{samples[0]+1},{samples[1]+1}"
        data = {}
        text = f":TRACE:{axis}? TR{trace}{area}"
        for axis in axes:
            match self.config['data']:
                case 'REAL,64':
                    data[axis] = self.adapter.connection.query_binary_values(
                        text,
                        'd')
                case 'REAL,32':
                    data[axis] = self.adapter.connection.query_binary_values(
                        text)
                case 'ASCII' | _:
                    data[axis] = self.adapter.ask_values(text)
        return data

    def getAnalysis(self):
        """Get the shown analysis data and return a list."""
        self.write(":CALC:DATA?")
        return self.adapter.ask_values()
