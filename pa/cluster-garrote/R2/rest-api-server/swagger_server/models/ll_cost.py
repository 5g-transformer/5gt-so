# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class LLCost(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, cost=None, ll=None):  # noqa: E501
        """LLCost - a model defined in Swagger

        :param cost: The cost of this LLCost.  # noqa: E501
        :type cost: float
        :param ll: The ll of this LLCost.  # noqa: E501
        :type ll: str
        """
        self.swagger_types = {
            'cost': float,
            'll': str
        }

        self.attribute_map = {
            'cost': 'cost',
            'll': 'LL'
        }

        self._cost = cost
        self._ll = ll

    @classmethod
    def from_dict(cls, dikt):
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The LLCost of this LLCost.  # noqa: E501
        :rtype: LLCost
        """
        return util.deserialize_model(dikt, cls)

    @property
    def cost(self):
        """Gets the cost of this LLCost.

        Cost of Mbps in the referenced LL  # noqa: E501

        :return: The cost of this LLCost.
        :rtype: float
        """
        return self._cost

    @cost.setter
    def cost(self, cost):
        """Sets the cost of this LLCost.

        Cost of Mbps in the referenced LL  # noqa: E501

        :param cost: The cost of this LLCost.
        :type cost: float
        """
        if cost is None:
            raise ValueError("Invalid value for `cost`, must not be `None`")  # noqa: E501

        self._cost = cost

    @property
    def ll(self):
        """Gets the ll of this LLCost.

        NFVIPoPs LL identifier  # noqa: E501

        :return: The ll of this LLCost.
        :rtype: str
        """
        return self._ll

    @ll.setter
    def ll(self, ll):
        """Sets the ll of this LLCost.

        NFVIPoPs LL identifier  # noqa: E501

        :param ll: The ll of this LLCost.
        :type ll: str
        """
        if ll is None:
            raise ValueError("Invalid value for `ll`, must not be `None`")  # noqa: E501

        self._ll = ll
