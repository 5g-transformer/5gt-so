# Author: Jordi Baranda
# Copyright (C) 2019 CTTC/CERCA
# License: To be defined. Currently use is restricted to partners of the 5G-Transformer project,
#          http://5g-transformer.eu/, no use or redistribution of any kind outside the 5G-Transformer project is
#          allowed.
# Disclaimer: this software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.

# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.ns_scale_info_im import NsScaleInfoIm  # noqa: F401,E501
from swagger_server import util


class ScaleNsToLevelDataIm(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, ns_instantiation_level: str=None, ns_scale_info: List[NsScaleInfoIm]=None):  # noqa: E501
        """ScaleNsToLevelDataIm - a model defined in Swagger

        :param ns_instantiation_level: The ns_instantiation_level of this ScaleNsToLevelDataIm.  # noqa: E501
        :type ns_instantiation_level: str
        :param ns_scale_info: The ns_scale_info of this ScaleNsToLevelDataIm.  # noqa: E501
        :type ns_scale_info: List[NsScaleInfoIm]
        """
        self.swagger_types = {
            "ns_instantiation_level": str,
            "ns_scale_info": List[NsScaleInfoIm]
        }

        self.attribute_map = {
            "ns_instantiation_level": "nsInstantiationLevel",
            "ns_scale_info": "nsScaleInfo"
        }

        self._ns_instantiation_level = ns_instantiation_level
        self._ns_scale_info = ns_scale_info

    @classmethod
    def from_dict(cls, dikt) -> "ScaleNsToLevelDataIm":
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The ScaleNsToLevelData_im of this ScaleNsToLevelDataIm.  # noqa: E501
        :rtype: ScaleNsToLevelDataIm
        """
        return util.deserialize_model(dikt, cls)

    @property
    def ns_instantiation_level(self) -> str:
        """Gets the ns_instantiation_level of this ScaleNsToLevelDataIm.


        :return: The ns_instantiation_level of this ScaleNsToLevelDataIm.
        :rtype: str
        """
        return self._ns_instantiation_level

    @ns_instantiation_level.setter
    def ns_instantiation_level(self, ns_instantiation_level: str):
        """Sets the ns_instantiation_level of this ScaleNsToLevelDataIm.


        :param ns_instantiation_level: The ns_instantiation_level of this ScaleNsToLevelDataIm.
        :type ns_instantiation_level: str
        """

        self._ns_instantiation_level = ns_instantiation_level

    @property
    def ns_scale_info(self) -> List[NsScaleInfoIm]:
        """Gets the ns_scale_info of this ScaleNsToLevelDataIm.


        :return: The ns_scale_info of this ScaleNsToLevelDataIm.
        :rtype: List[NsScaleInfoIm]
        """
        return self._ns_scale_info

    @ns_scale_info.setter
    def ns_scale_info(self, ns_scale_info: List[NsScaleInfoIm]):
        """Sets the ns_scale_info of this ScaleNsToLevelDataIm.


        :param ns_scale_info: The ns_scale_info of this ScaleNsToLevelDataIm.
        :type ns_scale_info: List[NsScaleInfoIm]
        """

        self._ns_scale_info = ns_scale_info
