#!/usr/bin/env python

#############################################################################
##
# This file is part of Taurus
##
# http://taurus-scada.org
##
# Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
##
# Taurus is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
##
# Taurus is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
##
# You should have received a copy of the GNU Lesser General Public License
# along with Taurus.  If not, see <http://www.gnu.org/licenses/>.
##
#############################################################################
__all__ = ["CurvesPropertiesTool"]

from taurus.external.qt import QtGui, Qt
from taurus.external.qt import QtCore
from taurus.qt.qtcore.configuration import BaseConfigurableClass
from taurus_pyqtgraph.curveproperties import (
    get_properties_from_curves,
    set_properties_on_curves,
    CurvesAppearanceChooser,
)
import pyqtgraph


class CurvesPropertiesTool(QtGui.QAction, BaseConfigurableClass):
    """
    This tool inserts an action in the menu of the :class:`pyqtgraph.PlotItem`
    to which it is attached to show a dialog for editing curve properties.
    It is implemented as an Action, and provides a method to attach it to a
    PlotItem.
    """

    def __init__(self, parent=None):
        BaseConfigurableClass.__init__(self)
        QtGui.QAction.__init__(self, "Plot configuration", parent)
        self.triggered.connect(self._onTriggered)
        self.plot_item = None
        self.Y2Axis = None
        self.registerConfigProperty(
            self._getCurveAppearanceProperties,
            self._setCurveAppearanceProperties,
            "CurveProperties",
        )
        self.registerConfigProperty(
            self._getBackgroundColor,
            self._setBackgroundColor,
            "PlotBackground",
        )

    def _getBackgroundColor(self):
        try:
            return self.plot_item.scene().parent().backgroundBrush().color()
        except:
            import taurus
            taurus.debug("Cannot get plot background. Revert to 'default'")
            return 'default'

    def _setBackgroundColor(self, color):
        self.plot_item.scene().parent().setBackground(color)

    def attachToPlotItem(self, plot_item, y2=None):
        """
        Use this method to add this tool to a plot

        :param plot_item: (PlotItem)
        :param y2: (Y2ViewBox) instance of the Y2Viewbox attached to plot_item
                   if the axis change controls are to be used
        """
        self.plot_item = plot_item
        menu = plot_item.getViewBox().menu
        menu.addAction(self)
        self.Y2Axis = y2

    def _onTriggered(self):
        props = self._getCurveAppearanceProperties()
        curves = self.getModifiableItems()

        dlg = Qt.QDialog(parent=self.parent())
        dlg.setWindowTitle("Plot Configuration")
        layout = Qt.QVBoxLayout()

        w = CurvesAppearanceChooser(
            parent=dlg,
            curvePropDict=props,
            curvesDict=curves,
            showButtons=True,
            plotItem=self.plot_item,
            Y2Axis=self.Y2Axis,
        )
        layout.addWidget(w)
        dlg.setLayout(layout)
        dlg.exec_()

    def getModifiableItems(self):
        data_items = self.plot_item.listDataItems()
        # checks in all ViewBoxes from plot_item,
        # looking for a data_items (Curves).

        for item in self.plot_item.scene().items():
            if isinstance(item, pyqtgraph.ViewBox):
                for data in item.addedItems:
                    if data not in data_items:
                        data_items.append(data)

        # The dialog will ignore curves that define `._UImodifiable=False`
        modifiable_items = {}
        for item in data_items:
            if getattr(item, "_UImodifiable", True):
                modifiable_items[item.name()] = item
        return modifiable_items

    def _getCurveAppearanceProperties(self):
        return get_properties_from_curves(self.getModifiableItems())

    def _setCurveAppearanceProperties(self, props):
        curves = self.getModifiableItems()
        set_properties_on_curves(
            props, curves, plotItem=self.plot_item, y2Axis=self.Y2Axis
        )


if __name__ == "__main__":
    import sys
    import numpy
    import pyqtgraph as pg
    from taurus.qt.qtgui.tpg import TaurusPlotDataItem
    from taurus.qt.qtgui.application import TaurusApplication

    app = TaurusApplication()

    # a standard pyqtgraph plot_item
    w = pg.PlotWidget()

    # add legend to the plot, for that we have to give a name to plot items
    w.addLegend()

    # add a Y2 axis
    from taurus.qt.qtgui.tpg import Y2ViewBox

    y2ViewBox = Y2ViewBox()
    y2ViewBox.attachToPlotItem(w.getPlotItem())

    # adding a regular data item (non-taurus)
    c1 = pg.PlotDataItem(
        name="st plot",
        pen=dict(color="y", width=3, style=QtCore.Qt.DashLine),
        fillLevel=0.3,
        fillBrush="g",
    )

    c1.setData(numpy.arange(300) / 300.0)
    w.addItem(c1)

    # adding a taurus data item
    c2 = TaurusPlotDataItem(
        name="st2 plot", pen="r", symbol="o", symbolSize=10
    )
    c2.setModel("sys/tg_test/1/wave")

    w.addItem(c2)

    # attach tool to plot item of the PlotWidget
    tool = CurvesPropertiesTool()
    tool.attachToPlotItem(w.getPlotItem(), y2=y2ViewBox)

    w.show()

    # directly trigger the tool
    tool.trigger()

    sys.exit(app.exec_())
