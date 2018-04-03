# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from copy import deepcopy

import numpy as np
from astropy.utils import lazyproperty, deprecated

from ..utils.colormaps import random_cmap


__all__ = ['SourceSegment', 'SegmentationImage']

__doctest_requires__ = {('SegmentationImage', 'SegmentationImage.*'):
                        ['scipy', 'skimage']}


class SourceSegment(object):
    """
    Class for a single labeled region within a segmentation image.

    Parameters
    ----------
    label : int
        The source segment label number.

    slices : tuple of two slices
        A tuple of two slices representing the minimal box that contains
        the labeled region.

    area : float
        The area of the source segment in pixels**2.
    """

    def __init__(self, label, slices, area):
        self.label = label
        self.slices = slices
        self.area = area


class SegmentationImage(object):
    """
    Class for a segmentation image.

    Parameters
    ----------
    data : array_like (int)
        A 2D segmentation image where sources are labeled by different
        positive integer values.  A value of zero is reserved for the
        background.
    """

    def __init__(self, data):
        self.data = np.asanyarray(data, dtype=np.int)

    @lazyproperty
    def source_segments(self):
        """
        A list of `SourceSegment` objects.

        The returned list has a length equal to 1 plus the maximum label
        number.  If a label number is missing from the segmentation
        image, then `None` is returned instead of a `SourceSegment`
        object.
        """

        if not hasattr(self, '_source_segments'):
            self._create_source_segments()
        return self._source_segments

    def __getitem__(self, index):
        return self.source_segments[index]

    # python 2 only
    def __getslice__(self, i, j):
        return self.__getitem__(slice(i, j))

    def __iter__(self):
        for i in self.source_segments:
            yield i

    def _create_source_segments(self):
        """Create a list of `SourceSegment` objects."""

        source_segms = []
        for i, slc in enumerate(self.slices):
            if slc is None:
                source_segms.append(None)
            else:
                source_segms.append(SourceSegment(i+1, slc, self.areas[i]))

        self._source_segments = source_segms

    @property
    def data(self):
        """
        The 2D segmentation image.
        """

        return self._data

    @data.setter
    def data(self, value):
        if np.min(value) < 0:
            raise ValueError('The segmentation image cannot contain '
                             'negative integers.')

        if '_data' in self.__dict__:
            # needed only when data is reassigned, not on init
            self._reset_lazy_properties()

        self._data = value

    def _reset_lazy_properties(self):
        """Reset all lazy properties."""
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, lazyproperty):
                self.__dict__.pop(key, None)

    @property
    def array(self):
        """
        The 2D segmentation image.
        """

        return self._data

    def __array__(self):
        """
        Array representation of the segmentation image (e.g., for
        matplotlib).
        """

        return self._data

    @lazyproperty
    @deprecated(0.5, alternative='data_ma')
    def data_masked(self):
        return self.data_ma  # pragma: no cover

    @lazyproperty
    def data_ma(self):
        """
        A `~numpy.ma.MaskedArray` version of the segmentation image
        where the background (label = 0) has been masked.
        """

        return np.ma.masked_where(self.data == 0, self.data)

    @staticmethod
    def _labels(data):
        """
        Return a sorted array of the non-zero labels in the segmentation
        image.

        Parameters
        ----------
        data : array_like (int)
            A 2D segmentation image where sources are labeled by
            different positive integer values.  A value of zero is
            reserved for the background.

        Returns
        -------
        result : `~numpy.ndarray`
            An array of non-zero label numbers.

        Notes
        -----
        This is a separate static method so it can be used on masked
        versions of the segmentation image (cf.
        ``~photutils.SegmentationImage.remove_masked_labels``.

        Examples
        --------
        >>> from photutils import SegmentationImage
        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> segm._labels(segm.data)
        array([1, 3, 4, 5, 7])
        """

        # np.unique also sorts elements
        return np.unique(data[data != 0])

    @lazyproperty
    def shape(self):
        """
        The shape of the 2D segmentation image.
        """

        return self._data.shape

    @lazyproperty
    def labels(self):
        """The sorted non-zero labels in the segmentation image."""

        return self._labels(self.data)

    @lazyproperty
    def nlabels(self):
        """The number of non-zero labels in the segmentation image."""

        return len(self.labels)

    @lazyproperty
    @deprecated(0.5, alternative='max_label')
    def max(self):
        return self.max_label  # pragma: no cover

    @lazyproperty
    def max_label(self):
        """The maximum non-zero label in the segmentation image."""

        return np.max(self.labels)

    @lazyproperty
    def slices(self):
        """
        A list of tuples, where each tuple contains two slices
        representing the minimal box that contains the labeled region.

        The list starts with the *non-zero* label.  The returned list
        has a length equal to the maximum label number.  If a label
        number is missing, then `None` is returned for that list element
        instead of a slice.
        """

        from scipy.ndimage import find_objects

        return find_objects(self._data)

    @lazyproperty
    def areas(self):
        """
        A 1D array of areas (in pixel**2) of the non-zero labeled
        regions.

        The `~numpy.ndarray` starts with the *non-zero* label The
        returned array has a length equal to the maximum label number.
        If a label number is missing, then 0 is returned for that array
        element.
        """

        return np.bincount(self.data.ravel())[1:]

    @deprecated(0.5, alternative='areas[labels-1]')
    def area(self, labels):  # pragma: no cover
        """
        The areas (in pixel**2) of the regions for the input labels.

        Parameters
        ----------
        labels : int, array-like (1D, int)
            The label(s) for which to return areas.

        Returns
        -------
        areas : `~numpy.ndarray`
            The areas of the labeled regions.
        """

        labels = np.atleast_1d(labels)
        for label in labels:
            self.check_label(label, allow_zero=True)
        return self.areas[labels - 1]

    @lazyproperty
    @deprecated(0.5, alternative='is_consecutive')
    def is_sequential(self):
        return self.is_consecutive  # pragma: no cover

    @lazyproperty
    def is_consecutive(self):
        """
        Determine whether or not the non-zero labels in the segmenation
        image are consecutive (i.e. no missing values).
        """

        if (self.labels[-1] - self.labels[0] + 1) == self.nlabels:
            return True
        else:
            return False

    @lazyproperty
    def missing_labels(self):
        """
        A 1D `~numpy.ndarray` of the sorted non-zero labels that are
        missing in the consecutive sequence from zero to the maximum
        label number.
        """

        return np.array(sorted(set(range(0, self.max_label + 1)).
                               difference(np.insert(self.labels, 0, 0))))

    def copy(self):
        """
        Return a deep copy of this class instance.
        """

        return deepcopy(self)

    def check_label(self, label, allow_zero=False):
        """
        Check for a valid label label number within the segmentation
        image.

        Parameters
        ----------
        label : int
            The label number to check.

        allow_zero : bool
            If `True` then a label of 0 is valid, otherwise 0 is
            invalid.

        Raises
        ------
        ValueError
            If the input ``label`` is invalid.
        """

        if label == 0:
            if allow_zero:
                return
            else:
                raise ValueError('label "0" is reserved for the background')

        if label < 0:
            raise ValueError('label must be a positive integer, got '
                             '"{0}"'.format(label))
        if label not in self.labels:
            raise ValueError('label "{0}" is not in the segmentation '
                             'image'.format(label))

    def cmap(self, background_color='#000000', random_state=None):
        """
        A matplotlib colormap consisting of random (muted) colors.

        This is very useful for plotting the segmentation image.

        Parameters
        ----------
        background_color : str or `None`, optional
            A hex string in the "#rrggbb" format defining the first
            color in the colormap.  This color will be used as the
            background color (label = 0) when plotting the segmentation
            image.  The default is black.

        random_state : int or `~numpy.random.RandomState`, optional
            The pseudo-random number generator state used for random
            sampling.  Separate function calls with the same
            ``random_state`` will generate the same colormap.
        """

        from matplotlib import colors

        cmap = random_cmap(self.max_label + 1, random_state=random_state)

        if background_color is not None:
            cmap.colors[0] = colors.hex2color(background_color)

        return cmap

    def outline_segments(self, mask_background=False):
        """
        Outline the labeled segments.

        The "outlines" represent the pixels *just inside* the segments,
        leaving the background pixels unmodified.  This corresponds to
        the ``mode='inner'`` in `skimage.segmentation.find_boundaries`.

        Parameters
        ----------
        mask_background : bool, optional
            Set to `True` to mask the background pixels (labels = 0) in
            the returned image.  This is useful for overplotting the
            segment outlines on an image.  The default is `False`.

        Returns
        -------
        boundaries : 2D `~numpy.ndarray` or `~numpy.ma.MaskedArray`
            An image with the same shape of the segmenation image
            containing only the outlines of the labeled segments.  The
            pixel values in the outlines correspond to the labels in the
            segmentation image.  If ``mask_background`` is `True`, then
            a `~numpy.ma.MaskedArray` is returned.

        Examples
        --------
        >>> from photutils import SegmentationImage
        >>> segm = SegmentationImage([[0, 0, 0, 0, 0, 0],
        ...                           [0, 2, 2, 2, 2, 0],
        ...                           [0, 2, 2, 2, 2, 0],
        ...                           [0, 2, 2, 2, 2, 0],
        ...                           [0, 2, 2, 2, 2, 0],
        ...                           [0, 0, 0, 0, 0, 0]])
        >>> segm.outline_segments()
        array([[0, 0, 0, 0, 0, 0],
               [0, 2, 2, 2, 2, 0],
               [0, 2, 0, 0, 2, 0],
               [0, 2, 0, 0, 2, 0],
               [0, 2, 2, 2, 2, 0],
               [0, 0, 0, 0, 0, 0]])
        """

        # requires scikit-image >= 0.11
        from skimage.segmentation import find_boundaries

        outlines = self.data * find_boundaries(self.data, mode='inner')
        if mask_background:
            outlines = np.ma.masked_where(outlines == 0, outlines)
        return outlines

    def relabel(self, labels, new_label):
        """
        Relabel one or more label numbers.

        The input ``labels`` will all be relabeled to ``new_label``.

        Parameters
        ----------
        labels : int, array-like (1D, int)
            The label numbers(s) to relabel.

        new_label : int
            The relabeled label number.

        Examples
        --------
        >>> from photutils import SegmentationImage
        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> segm.relabel(labels=[1, 7], new_label=2)
        >>> segm.data
        array([[2, 2, 0, 0, 4, 4],
               [0, 0, 0, 0, 0, 4],
               [0, 0, 3, 3, 0, 0],
               [2, 0, 0, 0, 0, 5],
               [2, 2, 0, 5, 5, 5],
               [2, 2, 0, 0, 5, 5]])
        """

        labels = np.atleast_1d(labels)
        for label in labels:
            data = self.data
            data[np.where(data == label)] = new_label
            self.data = data     # needed to call the data setter

    @deprecated(0.5, alternative='relabel_consecutive()')
    def relabel_sequential(self, start_label=1):
        return self.relabel_consecutive(start_label=start_label)  # pragma: no cover

    def relabel_consecutive(self, start_label=1):
        """
        Relabel the label numbers consecutively, such that there are no
        missing label numbers (up to the maximum label number).

        Parameters
        ----------
        start_label : int, optional
            The starting label number, which should be a positive
            integer.  The default is 1.

        Examples
        --------
        >>> from photutils import SegmentationImage
        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> segm.relabel_consecutive()
        >>> segm.data
        array([[1, 1, 0, 0, 3, 3],
               [0, 0, 0, 0, 0, 3],
               [0, 0, 2, 2, 0, 0],
               [5, 0, 0, 0, 0, 4],
               [5, 5, 0, 4, 4, 4],
               [5, 5, 0, 0, 4, 4]])
        """

        if start_label <= 0:
            raise ValueError('start_label must be > 0.')

        if self.is_consecutive and (self.labels[0] == start_label):
            return

        forward_map = np.zeros(self.max_label + 1, dtype=np.int)
        forward_map[self.labels] = np.arange(self.nlabels) + start_label
        self.data = forward_map[self.data]

    def keep_labels(self, labels, relabel=False):
        """
        Keep only the specified label numbers.

        Parameters
        ----------
        labels : int, array-like (1D, int)
            The label number(s) to keep.  Labels of zero and those not
            in the segmentation image will be ignored.

        relabel : bool, optional
            If `True`, then the segmentation image will be relabeled
            such that the labels are in consecutive order starting from
            1.

        Examples
        --------
        >>> from photutils import SegmentationImage
        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> segm.keep_labels(labels=3)
        >>> segm.data
        array([[0, 0, 0, 0, 0, 0],
               [0, 0, 0, 0, 0, 0],
               [0, 0, 3, 3, 0, 0],
               [0, 0, 0, 0, 0, 0],
               [0, 0, 0, 0, 0, 0],
               [0, 0, 0, 0, 0, 0]])

        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> segm.keep_labels(labels=[5, 3])
        >>> segm.data
        array([[0, 0, 0, 0, 0, 0],
               [0, 0, 0, 0, 0, 0],
               [0, 0, 3, 3, 0, 0],
               [0, 0, 0, 0, 0, 5],
               [0, 0, 0, 5, 5, 5],
               [0, 0, 0, 0, 5, 5]])
        """

        labels = np.atleast_1d(labels)
        labels_tmp = list(set(self.labels) - set(labels))
        self.remove_labels(labels_tmp, relabel=relabel)

    def remove_labels(self, labels, relabel=False):
        """
        Remove one or more label numbers.

        Parameters
        ----------
        labels : int, array-like (1D, int)
            The label number(s) to remove.  Labels of zero and those not
            in the segmentation image will be ignored.

        relabel : bool, optional
            If `True`, then the segmentation image will be relabeled
            such that the labels are in consecutive order starting from
            1.

        Examples
        --------
        >>> from photutils import SegmentationImage
        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> segm.remove_labels(labels=5)
        >>> segm.data
        array([[1, 1, 0, 0, 4, 4],
               [0, 0, 0, 0, 0, 4],
               [0, 0, 3, 3, 0, 0],
               [7, 0, 0, 0, 0, 0],
               [7, 7, 0, 0, 0, 0],
               [7, 7, 0, 0, 0, 0]])

        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> segm.remove_labels(labels=[5, 3])
        >>> segm.data
        array([[1, 1, 0, 0, 4, 4],
               [0, 0, 0, 0, 0, 4],
               [0, 0, 0, 0, 0, 0],
               [7, 0, 0, 0, 0, 0],
               [7, 7, 0, 0, 0, 0],
               [7, 7, 0, 0, 0, 0]])
        """

        self.relabel(labels, new_label=0)
        if relabel:
            self.relabel_consecutive()

    def remove_border_labels(self, border_width, partial_overlap=True,
                             relabel=False):
        """
        Remove labeled segments near the image border.

        Labels within the defined border region will be removed.

        Parameters
        ----------
        border_width : int
            The width of the border region in pixels.

        partial_overlap : bool, optional
            If this is set to `True` (the default), a segment that
            partially extends into the border region will be removed.
            Segments that are completely within the border region are
            always removed.

        relabel : bool, optional
            If `True`, then the segmentation image will be relabeled
            such that the labels are in consecutive order starting from
            1.

        Examples
        --------
        >>> from photutils import SegmentationImage
        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> segm.remove_border_labels(border_width=1)
        >>> segm.data
        array([[0, 0, 0, 0, 0, 0],
               [0, 0, 0, 0, 0, 0],
               [0, 0, 3, 3, 0, 0],
               [0, 0, 0, 0, 0, 0],
               [0, 0, 0, 0, 0, 0],
               [0, 0, 0, 0, 0, 0]])

        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> segm.remove_border_labels(border_width=1,
        ...                           partial_overlap=False)
        >>> segm.data
        array([[0, 0, 0, 0, 0, 0],
               [0, 0, 0, 0, 0, 0],
               [0, 0, 3, 3, 0, 0],
               [7, 0, 0, 0, 0, 5],
               [7, 7, 0, 5, 5, 5],
               [7, 7, 0, 0, 5, 5]])
        """

        if border_width >= min(self.shape) / 2:
            raise ValueError('border_width must be smaller than half the '
                             'image size in either dimension')
        border = np.zeros(self.shape, dtype=np.bool)
        border[:border_width, :] = True
        border[-border_width:, :] = True
        border[:, :border_width] = True
        border[:, -border_width:] = True
        self.remove_masked_labels(border, partial_overlap=partial_overlap,
                                  relabel=relabel)

    def remove_masked_labels(self, mask, partial_overlap=True,
                             relabel=False):
        """
        Remove labeled segments located within a masked region.

        Parameters
        ----------
        mask : array_like (bool)
            A boolean mask, with the same shape as the segmentation
            image (``.data``), where `True` values indicate masked
            pixels.

        partial_overlap : bool, optional
            If this is set to `True` (the default), a segment that
            partially extends into a masked region will also be removed.
            Segments that are completely within a masked region are
            always removed.

        relabel : bool, optional
            If `True`, then the segmentation image will be relabeled
            such that the labels are in consecutive order starting from
            1.

        Examples
        --------
        >>> from photutils import SegmentationImage
        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> mask = np.zeros_like(segm.data, dtype=np.bool)
        >>> mask[0, :] = True    # mask the first row
        >>> segm.remove_masked_labels(mask)
        >>> segm.data
        array([[0, 0, 0, 0, 0, 0],
               [0, 0, 0, 0, 0, 0],
               [0, 0, 3, 3, 0, 0],
               [7, 0, 0, 0, 0, 5],
               [7, 7, 0, 5, 5, 5],
               [7, 7, 0, 0, 5, 5]])

        >>> segm = SegmentationImage([[1, 1, 0, 0, 4, 4],
        ...                           [0, 0, 0, 0, 0, 4],
        ...                           [0, 0, 3, 3, 0, 0],
        ...                           [7, 0, 0, 0, 0, 5],
        ...                           [7, 7, 0, 5, 5, 5],
        ...                           [7, 7, 0, 0, 5, 5]])
        >>> segm.remove_masked_labels(mask, partial_overlap=False)
        >>> segm.data
        array([[0, 0, 0, 0, 4, 4],
               [0, 0, 0, 0, 0, 4],
               [0, 0, 3, 3, 0, 0],
               [7, 0, 0, 0, 0, 5],
               [7, 7, 0, 5, 5, 5],
               [7, 7, 0, 0, 5, 5]])
        """

        if mask.shape != self.shape:
            raise ValueError('mask must have the same shape as the '
                             'segmentation image')
        remove_labels = self._labels(self.data[mask])
        if not partial_overlap:
            interior_labels = self._labels(self.data[~mask])
            remove_labels = list(set(remove_labels) - set(interior_labels))
        self.remove_labels(remove_labels, relabel=relabel)
