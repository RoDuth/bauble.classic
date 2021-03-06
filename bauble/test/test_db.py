# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

from bauble.test import BaubleTestCase
import bauble.plugins.plants.genus
import bauble.plugins.garden.accession

from bauble.db import class_of_object


class GlobalFunctionsTests(BaubleTestCase):
    def test_get_next_code_first_this_year(self):
        self.assertEquals(class_of_object("genus"),
                          bauble.plugins.plants.genus.Genus)
        self.assertEquals(class_of_object("accession_note"),
                          bauble.plugins.garden.accession.AccessionNote)
        self.assertEquals(class_of_object("not_existing"), None)
