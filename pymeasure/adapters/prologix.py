#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2016 PyMeasure Developers
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

from pymeasure.adapters.serial import SerialAdapter

import serial
from time import sleep


class PrologixAdapter(SerialAdapter):
    """ Encapsulates the additional commands necessary
    to communicate over a Prologix GPIB-USB Adapter,
    using the SerialAdapter.

    Each PrologixAdapter is constructed based on a serial port or
    connection and the GPIB address to be communicated to.
    Serial connection sharing is achieved by using the :meth:`.gpib`
    method to spawn new PrologixAdapters for different GPIB addresses.

    :param port: The Serial port name or a serial.Serial object
    :param address: Integer GPIB address of the desired instrument
    :param kwargs: Key-word arguments if constructing a new serial object
    
    :ivar address: Integer GPIB address of the desired instrument

    To allow user access to the Prologix adapter in Linux, create the file:
    :code:`/etc/udev/rules.d/51-prologix.rules`, with contents:
    
    .. code-block:: bash

        SUBSYSTEMS=="usb",ATTRS{idVendor}=="0403",ATTRS{idProduct}=="6001",MODE="0666"
    
    Then reload the udev rules with:

    .. code-block:: bash

        sudo udevadm control --reload-rules
        sudo udevadm trigger
    
    """
    def __init__(self, port, address=None, **kwargs):
        self.address = address
        if isinstance(port, serial.Serial):
            # A previous adapter is sharing this connection
            self.connection = port
        else:
            # Construct a new connection
            self.connection = serial.Serial(port, 9600, timeout=0.5, **kwargs)
            self.set_defaults()

    def set_defaults(self):
        """ Sets up the default behavior of the Prologix-GPIB
        adapter
        """
        self.write("++auto 0")  # Turn off auto read-after-write
        self.write("++eoi 1")  # Append end-of-line to commands
        self.write("++eos 2")  # Append line-feed to commands

    def __del__(self):
        """ Ensures that the Serial connection is closed upon object
        deletion if it is open
        """
        if self.connection.isOpen():
            self.connection.close()

    def write(self, command):
        """ Writes the command to the GPIB address stored in the
        :attr:`.address`

        :param command: SCPI command string to be sent to the instrument
        """
        if self.address is not None:
            address_command = "++addr %d\n" % self.address
            self.connection.write(address_command.encode())
        command += "\n"
        self.connection.write(command.encode())

    def read(self):
        """ Reads the response of the instrument until timeout

        :returns: String ASCII response of the instrument
        """
        self.write("++read")
        return b"\n".join(self.connection.readlines()).decode()

    def gpib(self, address):
        """ Returns and PrologixAdapter object that references the GPIB
        address specified, while sharing the Serial connection with other
        calls of this function

        :param address: Integer GPIB address of the desired instrument
        :returns: PrologixAdapter for specific GPIB address
        """
        return PrologixAdapter(self.connection, address)

    def wait_for_srq(self, timeout=25, delay=0.1):
        """ Blocks until a SRQ, and leaves the bit high

        :param timeout: Timeout duration in seconds
        :param delay: Time delay between checking SRQ in seconds
        """
        while int(self.ask("++srq")) != 1:  # TODO: Include timeout!
            sleep(delay)

    def __repr__(self):
        if self.address:
            return "<PrologixAdapter(port='%s',address=%d)>" % (
                    self.port, self.address)
        else:
            return "<PrologixAdapter(port='%s')>" % self.connection.port