This directory contains a portion of pySerial 2.5, distributed under the Python License; please see LICENSE.txt.

The changes made from the official pySerial distribution are as follows:
  - We are distributing only the "serial" directory of the original software.  
  - The license and README.txt files have been moved into the serial directory.
  - This README.txt has been modified with these notes about modifications, for compliance with the license.



Below follows the content of the original README.txt from the pySerial distribution:

==========
 pySerial
==========

Overview
========
This module encapsulates the access for the serial port. It provides backends
for Python running on Windows, Linux, BSD (possibly any POSIX compliant
system), Jython and IronPython (.NET and Mono). The module named "serial"
automatically selects the appropriate backend.

- Project Homepage: http://pyserial.sourceforge.net
- Project page on SourceForge: http://sourceforge.net/projects/pyserial/
- SVN repository: http://sourceforge.net/svn/?group_id=46487
- Download Page: http://sourceforge.net/project/showfiles.php?group_id=46487

BSD license, (C) 2001-2010 Chris Liechti <cliechti@gmx.net>


Documentation
=============
For API documentation, usage and examples see files in the "documentation"
directory.  The ".rst" files can be read in any text editor or being converted to
HTML or PDF using Sphinx. An online HTML version is at
http://pyserial.sourceforge.net.


Examples
========
Examples and unit tests are in the directory "examples".


Installation
============
Detailed information can be found in "documentation/pyserial.rst".

The usual setup.py for Python libraries is used for the source distribution.
Windows installers are also available (see download link above).
