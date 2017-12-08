# -*- coding: utf-8 -*-
"""
Logger module

Author: Peter Pakos <peter.pakos@wandisco.com>

Copyright (C) 2017 WANdisco

This file is part of ipa_check_consistency.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import logging


def get_logger(dir_name=None, file_name=None, debug=False, verbose=False, quiet=False, console_level='INFO',
               file_level='INFO'):
    if not verbose:
        other_loggers = []
        for key in logging.Logger.manager.loggerDict:
            other_logger = str(key).split('.')[0]
            if other_logger not in other_loggers:
                other_loggers.append(other_logger)
        for other_logger in other_loggers:
            logging.getLogger(other_logger).propagate = False

    if not file_name:
        file_name = os.path.splitext(sys.modules['__main__'].__file__)[0] + '.log'

    if dir_name:
        log_file = '%s/%s' % (dir_name, file_name)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
    else:
        log_file = file_name

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if not quiet and console_level:
        if debug:
            console_formatter = logging.Formatter('%(asctime)s [%(module)s] %(levelname)s %(message)s')
        else:
            console_formatter = logging.Formatter('%(message)s')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if debug else getattr(logging, console_level.upper()))
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    if file_level:
        file_formatter = logging.Formatter('%(asctime)s [%(module)s] %(levelname)s %(message)s')
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(logging.DEBUG if debug else getattr(logging, file_level.upper()))
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
