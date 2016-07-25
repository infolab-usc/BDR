import logging
from collections import deque

import numpy as np

from Node import Node
from Params import Params
import sys
sys.path.append('../plot/code')

from Utils import is_rect_cover


class Generic(object):
    def __init__(self, data, param):
        self.param = param
        self.cell_count = 0
        # initialize the root
        self.root = Node()
        # self.children = [] # all level 2 grids
        self.root.n_data = data
        self.root.n_box = np.array([param.LOW, param.HIGH])

    def getEqualSplit(self, partitions, min, max):
        """return equal split points, including both ends"""
        if min > max:
            logging.debug("getEqualSplit: Error: min > max")
        if partitions <= 1:
            return [min, max]
        return [min + (max - min) * i / partitions for i in range(partitions + 1)]

    def getCoordinates(self, curr):
        """return the split dimension, the split points and the data points in each subnodes"""
        raise NotImplementedError

    def getCount(self, curr):
        if curr.n_data is None:
            count = 0
        else:
            count = curr.n_data.shape[1]

        return count

    def testLeaf(self, curr):
        """test whether a node is a leaf node"""
        raise NotImplementedError

    def intersect(self, hrect, query):
        """
        checks if the hyper-rectangle intersects with the
        hyper-rectangle defined by the query in every dimension
        """
        bool_m1 = query[0, :] >= hrect[1, :]
        bool_m2 = query[1, :] <= hrect[0, :]
        bool_m = np.logical_or(bool_m1, bool_m2)
        if np.any(bool_m):
            return False
        else:
            return True

    def buildIndex(self):
        self.root.n_count = self.getCount(self.root)
        queue = deque()
        queue.append(self.root)
        nleaf = 0  # number of leaf node, for debug only
        # ## main loop
        while len(queue) > 0:
            curr = queue.popleft()

            if self.testLeaf(curr) is True:  # if curr is a leaf node
                if curr.n_depth < self.param.maxHeightHTree:
                    curr.n_count = self.getCount(curr)
                curr.n_isLeaf = True

            else:  # curr needs to split
                split_arr, n_data_arr = self.getCoordinates(curr)
                if split_arr is None:
                    if curr.n_depth < self.param.maxHeightHTree:
                        curr.n_count = self.getCount(curr)
                    curr.n_isLeaf = True
                    curr.children = []
                    continue  # if the first level cell is leaf node
                print len(n_data_arr)
                for i in range(len(n_data_arr)):
                    node = Node()
                    if curr.n_depth % self.param.NDIM == 0:  # split by x coord
                        node.n_box = np.array([[split_arr[i], curr.n_box[0, 1]], [split_arr[i + 1], curr.n_box[1, 1]]])
                    else:  # split by y coord
                        node.n_box = np.array([[curr.n_box[0, 0], split_arr[i]], [curr.n_box[1, 0], split_arr[i + 1]]])

                    node.index = i
                    node.parent = curr
                    node.n_depth = curr.n_depth + 1
                    node.n_data = n_data_arr[i]
                    node.n_count = self.getCount(node)
                    curr.children.append(node)
                    queue.append(node)

                curr.n_data = None  # ## do not need the data points coordinates now
        # end of while

    def rangeCount(self, query):
        """
        Query answering function. Find the number of data points within a query rectangle.
        """
        queue = deque()
        queue.append(self.root)
        count = 0.0
        while len(queue) > 0:
            curr = queue.popleft()
            _box = curr.n_box
            if curr.n_isLeaf is True:
                frac = 1
                if self.intersect(_box, query):
                    for i in range(_box.shape[1]):
                        if _box[1, i] == _box[0, i]:
                            frac *= 1
                        else:
                            frac *= (min(query[1, i], _box[1, i]) - max(query[0, i], _box[0, i])) / (
                                _box[1, i] - _box[0, i])
                    count += curr.n_count * frac
            else:  # if not leaf
                for node in curr.children:
                    bool_matrix = np.zeros((2, query.shape[1]))
                    bool_matrix[0, :] = query[0, :] <= _box[0, :]
                    bool_matrix[1, :] = query[1, :] >= _box[1, :]

                    if np.all(bool_matrix):  # if query range contains node range
                        count += node.n_count
                    elif self.intersect(_box, query):
                        queue.append(node)
        return float(count)


    def leafCover(self, loc):
        """
        find a leaf node that cover the location
        """
        queue = deque()
        queue.append(self.root)
        while len(queue) > 0:
            curr = queue.popleft()
            _box = curr.n_box
            if curr.n_isLeaf is True:
                if is_rect_cover(_box, loc):
                    return curr
            else:  # if not leaf
                queue.extend(curr.children)


    def checkCorrectness(self, node, nodePoints=None):
        """
        Total number of data points of all leaf nodes should equal to the total data points
        """
        totalPoints = 0
        if node is None:
            return 0
        if node.n_isLeaf and node.n_data is not None:
            return node.n_data.shape[1]
        for child in node.children:
            totalPoints += self.checkCorrectness(child)

        if nodePoints is None:
            return totalPoints

        if totalPoints == nodePoints:
            return True
        return False