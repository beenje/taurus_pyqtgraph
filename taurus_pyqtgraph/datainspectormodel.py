from datetime import datetime

from pyqtgraph import TextItem, InfiniteLine
import numpy as np
from taurustrendset import TaurusTrendSet


class DataInspectorModel(object):
    """
    DataInspectorModel is a general class use to point-picking.
    This class use a numpy library to finding the nearest point
    from the :class:`pyqtgraph.InfiniteLine`.
    Attach two widget to the plot:
        - :class:`pyqtgraph.InfiniteLine` - to selecting point
        - :class:`pyqtgraph.TextItem` - to showing the x,y value
    Also this class blink the selected scatter point item.
    """
    def __init__(self, trigger_point_size=20, default_point_size=10):

        self._scatter = {}
        self._information_clouds = {}
        # Maybe good idea is give user's access
        # to they have possibility to change the cloud style?
        self.cloud_style = "background-color: #35393C;"
        self._custom_point_style_init = {}

        self.date_format = "%Y-%m-%d %H:%M:%S"

        self.trigger_point_size = trigger_point_size
        self.default_point_size = default_point_size

        self._v_line = InfiniteLine(angle=90, movable=False)
        self.plot = None

    def attachPlot(self, plot):
        self.plot = plot
        self.plot.addItem(self._v_line, ignoreBounds=True)

    def detachPlot(self):
        self.detach()
        # Reset the dynamic creating the variables for future use the
        # attachToPlot method
        self._custom_point_style_init = {}
        self._scatter = {}
        self._information_clouds = {}

    def __del__(self):
        """
        Destructor which removing all data inspector item's
        """
        self.detach()

    def mouseMoved(self, evt):
        """
        Slot use to handle the mouse move event, and preform the action
        on the plot.

        :param evt: mouse event
        """
        pos = evt[0]

        if self.plot.sceneBoundingRect().contains(pos):
            mousePoint = self.plot.vb.mapSceneToView(pos)

            # Move InfiniteLine to the new position
            self._v_line.setPos(mousePoint.x())

            # Iteration over each curves in the plot and checking
            # that mouse point if is near the x axis date
            for i, curve in enumerate(filter(lambda o: not isinstance(o, TaurusTrendSet),
                                             self.plot.curves)):

                curve_data = curve.getData()
                curve_x_data = curve_data[0]
                curve_y_data = curve_data[1]

                # Getting the nearest point in the x axis
                # (if exist - empty array if not)
                point_index = self._getPointIndex(curve_x_data, mousePoint.x())
                if len(point_index) > 0:

                    point_x = curve_x_data[point_index][0]
                    point_y = curve_y_data[point_index][0]
                    try:
                        # Painting the cloud with the values of
                        # the selected data and blink the point base
                        # on the i values which is the index of current curve
                        self._paintCloud(point_x, point_y, i)
                        self._triggerPoint(curve, point_index, i)

                    except KeyError:

                        # Create the TextItem object for current curve and init
                        # the point style
                        self._information_clouds[i] = TextItem()

                        parent = self.plot.curves[i]
                        self._information_clouds[i].setParentItem(parent)

                        self._scatter[i] = curve.scatter
                        if curve.opts['symbol'] is None:
                            # create the custom style of the point
                            # if point style (symbol and size) not exist
                            curve.setSymbol('o')
                            curve.setSymbolSize(self.default_point_size)
                            self._custom_point_style_init[i] = True
                        else:
                            self._custom_point_style_init[i] = False

                        self._paintCloud(point_x, point_y, i)
                        self._triggerPoint(curve, point_index, i)

                else:
                    try:
                        # Clean the information cloud
                        # when the line isn't near any plot point
                        self._information_clouds[i].setText("")
                        curve.updateItems()
                    except KeyError:
                        pass

    def _paintCloud(self, x, y, i):
        """
        Method use to painting the cloud with the data

        :param x: the new x position of the picked point
        :param y: the new y position of the picked point
        :param i: the index of current curve
        """
        self._information_clouds[i].setPos(x, y)
        self._information_clouds[i].setHtml("<div style='%s'> "
                                            "<span>x=%s "
                                            "<span>y=%0.1f</span> "
                                            "</div>" % (self.cloud_style,
                                                        self._timestampToTime(x),
                                                        y))

    def _triggerPoint(self, curve, point_index, i):
        """
        Method use to trigger the point

        :param curve: is the reference to the current curve
        :param point_index: index of picked point
        :param i: the index of current curve
        """

        # Update itemas to make sure the older point is not still trigger
        curve.updateItems()
        scatterPoint = self._scatter[i].points()[point_index[0]]
        scatterPoint.setSize(self.trigger_point_size)

    def detach(self):
        """
        Removing the :class:`pyqtgraph.InfiniteLine` and
        :class:`pyqtgraph.TextItem` from the plot
        """
        self._resetCustomStyle()
        self.plot.scene().removeItem(self._v_line)
        for cloud in self._information_clouds.values():
            self.plot.scene().removeItem(cloud)

    @staticmethod
    def _getPointIndex(np_curve_data, mouse_point):
        """
        Helper method used to checking if the current mouse point coordinates
        are near the any point's in the curve

        :param np_curve_data: the array with the data (x or y)
        :param mouse_point: the current coordinates of the mouse (x or y)
        """
        point_picker = PointPicker(np_curve_data)
        return point_picker.checkPoint(mouse_point)

    def _timestampToTime(self, timestamp):
        """
        Method used to caste the timestamp from the curve to date
        in proper format (%Y-%m-%d %H:%M:%S)

        :param timestamp: selected timestamp from curve
        """
        return datetime.utcfromtimestamp(timestamp).strftime(self.date_format)

    def _resetCustomStyle(self):
        """
        If Date Inspector created the custom style this method reset the style
        during the disable process.
        """
        for i, curve in enumerate(filter(lambda o: not isinstance(o, TaurusTrendSet),
                                         self.plot.curves)):

            if i in range(0, len(self._custom_point_style_init.keys())):
                if self._custom_point_style_init[i]:
                    curve.setSymbolSize(0)
                    curve.setSymbol(None)


class PointPicker(np.ndarray):
    """
    Class use to handle the data with x or y date from curve and checking
    if the point is near or not (base on the roi) the current mouse point.
    This class extend the :class:`numpy.ndarray` to handle the numpy array
    with curve data.
    """
    def __new__(cls, *args, **kwargs):
        return np.array(*args, **kwargs).view(PointPicker)

    def checkPoint(self, point_to_check, roi=0.1):
        """
        Method use to checking if current point is near the point
        in the array date

        :param point_to_check: the currect point x or y co-ordinates
        :param roi: the tolerance limit
        :return: the index of the nearest point (empty array if not match)
        """
        pick_point = self[(point_to_check - roi < self) &
                          (point_to_check + roi > self)]
        if pick_point.size > 1:
            return self.checkPoint(point_to_check, roi-0.005)

        index = np.where(self == pick_point)
        return index[0]
