# Author: Luca Vettori
# Copyright (C) 2019 CTTC/CERCA
# License: To be defined. Currently use is restricted to partners of the 5G-Transformer project,
#          http://5g-transformer.eu/, no use or redistribution of any kind outside the 5G-Transformer project is
#          allowed.
# Disclaimer: this software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.

from flask import render_template, session
from functools import wraps


def login_passed(f):
    """
    Decorate method to check if the user is logged in the session.
    If not it return to the html login page
    :param f: function
    :return: decorate the parameter in case of success, or rendering of a html login page in case of not logged
    """
    @wraps(f)
    def decorate_func(*args, **kwargs):
        # uncomment/comment the below code to activate/deactivate login system access
        if not session.get('logged_in'):
            # link = request.path
            # return render_template('login.html', next=link)
            return render_template('login.html')
        else:
            return f(*args, **kwargs)

    return decorate_func
