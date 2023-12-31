# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from bugbug.models.component import ComponentModel


def test_get_component_labels():
    model = ComponentModel()
    classes, _ = model.get_labels()
    assert classes[1046231] == 1
    assert classes[1052536] != 1
