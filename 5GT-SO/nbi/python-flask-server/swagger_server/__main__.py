# Copyright 2018 CTTC www.cttc.es
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import hashlib
import json
from collections import OrderedDict

import connexion
from multiprocessing import set_start_method, Queue

import requests
import yaml
from datetime import timedelta
from flask import render_template, send_from_directory, request, session, flash, redirect, url_for, abort, send_file
from networkx.readwrite import json_graph
from swagger_server import encoder
from logging import getLogger
from os import path
import swagger_server.webserver_utils as gui_utils
from db.ns_db import ns_db
from db.nsd_db import nsd_db
from db.vnfd_db import vnfd_db
from db.appd_db import appd_db
from db.operation_db import operation_db
from db.nsir_db import nsir_db
from db.user_db import user_db
from sbi import sbi
from nbi import log_queue
from login_module.server_login import login_passed

from monitoring.webhook_receiver_alertmanager_sla import SLAManagerAPI

so_port = 8080
logger = getLogger("5gtso")
config_mtp_file = path.realpath(path.join(path.dirname(path.realpath(__file__)), '../../../mtp.properties'))
config_coremano_file = path.realpath(path.join(path.dirname(path.realpath(__file__)), '../../../coreMano/coreMano.properties'))
config_db_file = path.realpath(path.join(path.dirname(path.realpath(__file__)), '../../../db/db.properties'))
config_rooe_file = path.realpath(path.join(path.dirname(path.realpath(__file__)), '../../../sm/rooe/rooe.properties'))
config_monitoring_file = path.realpath(path.join(path.dirname(path.realpath(__file__)), '../../../monitoring/monitoring.properties'))
config_vs_file = path.realpath(path.join(path.dirname(path.realpath(__file__)), '../../../sm/soe/vs.properties'))
config_provider_domains_file = path.realpath(path.join(path.dirname(path.realpath(__file__)), '../../../sm/soe/federation.properties'))
local_swagger_ui_path = path.join(path.dirname(path.realpath(__file__)), 'swagger-ui-cttc')
options = {'swagger_path': local_swagger_ui_path}
app = connexion.App(__name__, specification_dir="./swagger/", options=options)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Register a new user for the SO platform.
    Allowed GET and POST methods.
    :return: rendering of the corresponding html page
    """
    # enter in the page by the GET method, only render the register.html page
    if request.method == 'GET':
        return render_template('register.html')
    # enter in the page by a POST method (filled the register page)
    else:
        username = request.form['username']
        password = request.form['password']
        password_confirmed = request.form['password_confirmed']
        if password != password_confirmed:
            logger.debug("Confirmed password is not the same!")
            flash('Confirmed password is not the same!', 'danger')
            return render_template("register.html")
        # hashing the password with md5
        user = user_db.get_specific_user({"username": username})
        # check if the entered 'user' is already in the db
        if user:
            log_queue.put(["DEBUG", "Username already in database".format(username)])
            flash('Username already registered', 'danger')
            return render_template("register.html")
        else:
            hash_object = hashlib.md5(password.encode())
            # insert the new user (and hashed password) in the db
            user_db.insert_user({"username": username, "password": hash_object.hexdigest(), "role": "Admin"})
            log_queue.put(["INFO", 'User "{}" successfully registered'.format(username)])
            flash('User "{}" successfully registered'.format(username), 'success')
            return render_template("login.html")


@app.route('/login', methods=['GET', 'POST'])
def do_admin_login():
    """
    Check if the entered user and password are in the db.
    Only allowed the POST method
    :return: redirect to main function of the main module
    """
    # enter in the page by the GET method, only render the login.html page
    if request.method == 'GET':
        return render_template('login.html')
    else:
        # enter in the page by a POST method (filled the register page)
        # next = request.form['next']
        username = str(request.form['username'])
        password = str(request.form['password'])

        # password has been hashed with md5 in the db, to avoid collecting in clear password
        hashed_password = hashlib.md5(password.encode())
        result = user_db.get_specific_user({"username": username, "password": hashed_password.hexdigest()})
        if result:
            session['logged_in'] = True
            session['user'] = username
            session['role'] = result['role']
            session.permanent = True  # uncomment/comment to activate/deactivate expiring session
            log_queue.put(["INFO", 'User "{}" logged correctly'.format(username)])
        else:
            flash('Username and/or Password are incorrect', 'warning')
            log_queue.put(["DEBUG", 'Username and/or Password are incorrect'])
        return redirect(url_for('home'))


@app.route("/logout")
def logout():
    """
    Perform the logout from GSO platform
    :return: rendering of the login html page
    """
    if 'user' in session:
        log_queue.put(["INFO", 'User "{}" logged out'.format(session['user'])])
        flash('User "{}" logged out'.format(session['user']), 'success')
        session['logged_in'] = False
        session.pop('user', None)
    return render_template("login.html")


@app.route('/favicon.ico')
def favicon():
    """
    To upload the favicon
    :return: send a file
    """
    return send_from_directory(path.join(path.dirname(path.realpath(__file__)), 'static/images'),
                               'favicon_cttc_blue.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/')
@app.route('/ui')
@login_passed
def home():
    """
    This function just responds to the browser Url
    :return:        the rendered template 'home.html'
    """
    # print(path.join(path.dirname(path.realpath(__file__)), 'static/images'))
    return render_template('home.html', html_title='Dashboard')


@app.route('/abs_view')
@login_passed
def abs_view():
    """
    This function just responds to the browser Url
    :return:        the rendered template 'abs_view.html'
    """
    abs_resources = {}
    fed_resources = {}
    # # attacking directly the REST API
    try:
        abs_resources = sbi.get_mtp_resources()
        fed_resources = sbi.get_mtp_federated_resources()
        # print(abs_resources)

    except(ConnectionError, TypeError) as e:
        log_queue.put(["ERROR", str(e)])
        flash("Problem with Abs Viewer: {}".format(e), 'danger')
        abort(408)
    # defining "local" pops and lls to be showed
    nfvi_pops = abs_resources['NfviPops']
    lls_list = abs_resources['logicalLinkInterNfviPops']
    # extend "federated" pops and lls
    nfvi_fed_pops = fed_resources['NfviPops']
    lls_list.extend(fed_resources['logicalLinkInterNfviPops'])
    abs_view_graph = gui_utils.abstracted_view_from_json(nfvi_pops, nfvi_fed_pops, lls_list)
    log_queue.put(["INFO", "Retrieved Abstracted Resource View from MTP!"])
    return render_template('abs_view.html',
                           html_title="Abstracted View",
                           d3_network=abs_view_graph)


@app.route('/databases/<string:table_name>', methods=['GET'])
@login_passed
def collections(table_name):
    """
    This function just responds to the browser Url
    :param table_name: string
    :return:        the rendered template 'tables.html'
    """
    if table_name not in ['ns', 'nsd', 'nsir', 'operation', 'resources', 'vnfd', 'user']:
        abort(404)
    users = user_db.get_all_user()
    vnfds = vnfd_db.get_all_vnfd()
    nsds = nsd_db.get_all_nsd()
    nss = ns_db.get_all_ns()
    nsirs = nsir_db.get_all_nsir()
    operations = operation_db.get_all_operation()
    return render_template('tables.html', html_title='Databases',
                           list_users=users,
                           list_vnfds=vnfds,
                           list_nsds=nsds,
                           list_nss=nss,
                           list_nsirs=nsirs,
                           list_operations=operations,
                           table_name=table_name)


@app.route('/delete_element', methods=['POST'])
@login_passed
def delete_element():
    if request.method == 'POST':
        table_to_choose = request.form['table_to_choose']
        id_to_be_deleted = request.form['id']
        if table_to_choose == "user":
            user_db.remove_user_by_id(id_to_be_deleted)
        elif table_to_choose == "vnfd":
            vnfd_db.remove_vnfd_by_id(id_to_be_deleted)
        elif table_to_choose == "nsd":
            nsd_db.remove_nsd_by_id(id_to_be_deleted)
        elif table_to_choose == "ns":
            ns_db.remove_ns_by_id(id_to_be_deleted)
        elif table_to_choose == "nsir":
            nsir_db.remove_nsir_by_id(id_to_be_deleted)
        elif table_to_choose == "operation":
            operation_db.remove_operation_by_id(id_to_be_deleted)
        message = {'Success': 'Deleted "{}" from "{}" table'.format(id_to_be_deleted, table_to_choose)}
        log_queue.put(["INFO", message['Success']])
        flash(message['Success'], 'success')
        return redirect(request.referrer)


@app.route('/modify_element', methods=['POST'])
@login_passed
def modify_element():
    """
    This function just responds to the browser Url
    :return:   redirect to the previous page
    """
    if request.method == 'POST':
        table_to_choose = request.form['table_to_choose']
        id_to_be_modified = request.form['id']
        body_update = {}
        for key, value in request.form.to_dict().items():
            if key == 'table_to_choose' or key == 'id':
                # keys not to be udpated in the table
                continue
            elif key == 'shareable':
                body_update[key] = eval(value)
            else:
                body_update[key] = value
        # print("body_update: {}".format(body_update))
        if table_to_choose == "user":
            user_db.update_user(id_to_be_modified, body_update)
        elif table_to_choose == "vnfd":
            vnfd_db.update_vnfd(id_to_be_modified, body_update)
        elif table_to_choose == "nsd":
            nsd_db.update_nsd(id_to_be_modified, body_update)
        elif table_to_choose == "ns":
            ns_db.update_ns(id_to_be_modified, body_update)
        elif table_to_choose == "nsir":
            nsir_db.update_nsir(id_to_be_modified, body_update)
        elif table_to_choose == "operation":
            operation_db.update_operation(id_to_be_modified, body_update)
        message = {'Success': 'Modified "{}" from "{}" table'.format(id_to_be_modified, table_to_choose)}
        log_queue.put(["INFO", message['Success']])
        flash(message['Success'], 'success')
        return redirect(request.referrer)


@app.route('/instantiate_nsd', methods=['POST'])
@login_passed
def instantiate_nsd():
    """
    This function instantiate the nsd
    :return:   redirect to the previous page
    """
    if request.method == 'POST':
        body_instantiate = {}
        for key, value in request.form.to_dict().items():
            body_instantiate[key] = value
        print("body_instantiate: {}".format(body_instantiate))
        # attacking directly the REST API
        rest_api_path_ns = "/5gt/so/v1/ns"
        headers = {
            "Content-type": "application/json"
        }
        try:
            body_ns_id = {
                "nsDescription": body_instantiate['nsDescription'],
                "nsName": body_instantiate['nsName'],
                "nsdId": body_instantiate['nsdId']
            }
            # creating nsId
            response_nsId = requests.post(url="http://localhost:{}{}".format(so_port, rest_api_path_ns),
                                          data=json.dumps(body_ns_id),
                                          headers=headers)
            # print(response_nsId.status_code, response_nsId.content)
            if response_nsId.status_code == 201:

                nsId = json.loads(response_nsId.content.decode('utf-8'))['nsId']
                print(nsId)
                message = {'Success': "Created nsId: '{}'".format(nsId)}
                log_queue.put(["INFO", message['Success']])
                flash(message['Success'], 'success')
                # instantiating the NS with the corresponding nsId and other parameters
                body_operation = {
                    "flavourId": body_instantiate['flavourId'],
                    "nsInstantiationLevelId": body_instantiate['nsInstantiationLevelId']
                }
                # if NSD is composite and a nested NS is already instantiated
                if 'nestedNsInstanceId' in body_instantiate:
                    if body_instantiate['nestedNsInstanceId']:
                        body_operation['nestedNsInstanceId'] = [body_instantiate['nestedNsInstanceId']]
                print("body_operation: {}".format(body_operation))
                response_instantiate = requests.put(url="http://localhost:{}{}/{}/instantiate".format(so_port,
                                                                                                      rest_api_path_ns,
                                                                                                      nsId),
                                                    data=json.dumps(body_operation),
                                                    headers=headers)
                if response_instantiate.status_code == 200:
                    operationId = json.loads(response_instantiate.content.decode('utf-8'))['operationId']
                    message = {'Success': "Instantiated NS with operationId: '{}'".format(operationId)}
                    log_queue.put(["INFO", message['Success']])
                    flash(message['Success'], 'success')
                else:
                    log_queue.put(["ERROR", "Error :{}, {}".format(response_instantiate.status_code,
                                                                 response_instantiate.content)])
                    raise ConnectionError("Error :{}, {}".format(response_instantiate.status_code,
                                                                 response_instantiate.content))

            else:
                log_queue.put(["ERROR", "Error :{}, {}".format(response_nsId.status_code, response_nsId.content)])
                raise ConnectionError("Error :{}, {}".format(response_nsId.status_code, response_nsId.content))
        except(ConnectionError, TypeError) as e:
            log_queue.put(["ERROR", str(e)])
            flash("Instantiation Failed: {}".format(e), 'danger')
            return redirect(request.referrer)
        return redirect(url_for('collections', table_name='ns'))


@app.route('/terminate_ns', methods=['POST'])
@login_passed
def terminate_ns():
    """
    This function terminate a ns
    :return:   redirect to the previous page
    """
    if request.method == 'POST':
        nsId = request.form['nsId']
        # attacking directly the REST API
        rest_api_path_ns = "/5gt/so/v1/ns"
        headers = {
            "Content-type": "application/json"
        }
        try:
            response_terminate = requests.put(url="http://localhost:{}{}/{}/terminate".format(so_port,
                                                                                                rest_api_path_ns,
                                                                                                nsId),
                                              headers=headers)
            if response_terminate.status_code == 200:
                operationId = json.loads(response_terminate.content.decode('utf-8'))['operationId']
                message = {'Success': "Terminated NS with operationId: '{}'".format(operationId)}
                log_queue.put(["INFO", message['Success']])
                flash(message['Success'], 'success')
            else:
                log_queue.put(["ERROR", "Error :{}, {}".format(response_terminate.status_code,
                                                               response_terminate.content)])
                raise ConnectionError("Error :{}, {}".format(response_terminate.status_code,
                                                             response_terminate.content))
        except(ConnectionError, TypeError) as e:
            log_queue.put(["ERROR", str(e)])
            flash("Instantiation Failed: {}".format(e), 'danger')
        return redirect(request.referrer)


@app.route('/config')
@login_passed
def display_config_files():
    with open(config_mtp_file, 'r') as myfile:
        lines = myfile.read().splitlines()
    data_1 = "\n".join(lines)
    with open(config_coremano_file, 'r') as myfile:
        lines = myfile.read().splitlines()
    data_2 = "\n".join(lines)
    with open(config_db_file, 'r') as myfile:
        lines = myfile.read().splitlines()
    data_3 = "\n".join(lines)
    with open(config_rooe_file, 'r') as myfile:
        lines = myfile.read().splitlines()
    data_4 = "\n".join(lines)
    with open(config_monitoring_file, 'r') as myfile:
        lines = myfile.read().splitlines()
    data_5 = "\n".join(lines)
    with open(config_vs_file, 'r') as myfile:
        lines = myfile.read().splitlines()
    data_6 = "\n".join(lines)
    with open(config_provider_domains_file, 'r') as myfile:
        lines = myfile.read().splitlines()
    data_7 = "\n".join(lines)
    return render_template('config_file_page.html',
                           html_title="Config Files",
                           config_1=data_1,
                           config_2=data_2,
                           config_3=data_3,
                           config_4=data_4,
                           config_5=data_5,
                           config_6=data_6,
                           config_7=data_7)


@app.route('/logs_popup')
@login_passed
def display_logs_popup():
    with open('5gtso.log', 'r') as myfile:
        lines = myfile.read().splitlines()
        last_lines = lines[-50:]
    last_lines.reverse()
    data = "\n".join(last_lines)
    return render_template('log_page.html',
                           logs=data)


@app.route('/ifa_converter', methods=['GET'])
@login_passed
def ifa_converter():
    """
    This function just responds to the browser Url
    :return: the rendered template 'ifa_conv.html'
    """

    if request.method == 'GET':
        return render_template('ifa_conv.html', html_title='IFA/OSM Converter')


@app.route('/descriptor_viewer', methods=['POST'])
@login_passed
def descriptor_viewer():
    """
    This function just responds to the browser Url
    :return: the rendered template 'descriptor.html'
    """
    if request.method == 'POST':
        try:
            already_onboarded_in_so = False
            # retrieving the IFA descriptor
            # print(request.form, request.files)
            if 'convert_text' in request.form:
                ifa_json = json.loads(request.form['convert_text'])
            elif 'file_to_convert' in request.files:
                f = request.files['file_to_convert']
                response = f.read()
                ifa_json = json.loads(response.decode('utf-8'))
            elif 'show_json' in request.form:
                ifa_json = eval(request.form['show_json'])
                already_onboarded_in_so = True
            elif 'onboard_json' in request.form:
                ifa_json = eval(request.form['onboard_json'])
                record = {}
                if 'nsd' in ifa_json:
                    # nsd case
                    if 'vnfdId' in ifa_json['nsd']:
                        record = {"nsdId": ifa_json["nsd"]["nsdIdentifier"],
                                  "nsdCloudifyId": {},
                                  "version": ifa_json["nsd"]["version"],
                                  "nsdName": ifa_json["nsd"]["nsdName"],
                                  "nsdJson": ifa_json,
                                  "shareable": True,
                                  "domain": "local"}
                        if nsd_db.get_nsd_json(nsdId=record['nsdId']) is None:
                            nsd_db.insert_nsd(record)
                            message = {"Success": 'nsdId : {} onboarded on SO with success!'.format(record['nsdId'])}
                        else:
                            log_queue.put(["DEBUG", 'nsdId already in the SO DB'])
                            raise ValueError('nsdId already in the SO DB')
                    # nsd-composite case
                    else:
                        record = {"nsdId": ifa_json["nsd"]["nsdIdentifier"],
                                  "nsdCloudifyId": {},
                                  "version": ifa_json["nsd"]["version"],
                                  "nsdName": ifa_json["nsd"]["nsdName"],
                                  "nsdJson": ifa_json,
                                  "shareable": False,
                                  "domain": "Composite"}
                        if nsd_db.get_nsd_json(nsdId=record['nsdId']) is None:
                            nsd_db.insert_nsd(record)
                            message = {"Success": 'nsdId : {} onboarded on SO with success!'.format(record['nsdId'])}
                        else:
                            log_queue.put(["DEBUG", 'nsdId already in the SO DB'])
                            raise ValueError('nsdId already in the SO DB')
                # vnfd case
                else:
                    record = {"vnfdId": ifa_json["vnfdId"],
                              "vnfdVersion": ifa_json["vnfdVersion"],
                              "vnfdName": ifa_json["vnfProductName"],
                              "vnfdJson": ifa_json}
                    if vnfd_db.get_vnfd_json(vnfdId=ifa_json["vnfdId"]) is None:
                        vnfd_db.insert_vnfd(record)
                        message = {'Success': 'vnfdId : {} onboarded on SO with success!'.format(record['vnfdId'])}
                    else:
                        log_queue.put(["DEBUG", 'vnfdId already in the SO DB'])
                        raise ValueError('vnfdId already in the SO DB')
                log_queue.put(["INFO", message["Success"]])
                flash(message['Success'], 'success')
                already_onboarded_in_so = True
            else:
                raise ValueError('No text/file valid')
            if 'nsd' in ifa_json:
                if 'vnfdId' in ifa_json['nsd']:
                    # convert a NSD
                    list_osm_json, default_index = gui_utils.ifa014_conversion(ifa_json)
                    default_osm_json = list_osm_json[default_index]
                    osm_json_network = []
                    for level in list_osm_json:
                        osm_json_network.append(json_graph.node_link_data(gui_utils.json_network_nsd(level)))
                    descriptor_type = 'nsd'
                else:
                    # convert a composite NSD
                    list_osm_json, default_index = gui_utils.composite_desc_conversion(ifa_json)
                    default_osm_json = list_osm_json[default_index]
                    osm_json_network = []
                    for level in list_osm_json:
                        osm_json_network.append(json_graph.node_link_data(gui_utils.json_network_composite_nsd(level)))
                    descriptor_type = 'nsd-composite'

            else:
                # convert a VNFD
                list_osm_json = [gui_utils.ifa011_conversion(ifa_json)]
                default_osm_json = list_osm_json[0]  # done in case of possible list of ifa vnfd conversion
                osm_json_network = [json_graph.node_link_data(gui_utils.json_network_vnfd(default_osm_json))]
                descriptor_type = 'vnfd'
            yaml_descriptor_list = []
            for osm_json in list_osm_json:
                yaml_descriptor_list.append(yaml.safe_dump(osm_json, default_flow_style=False))
            yaml_ifa_descriptor = yaml.safe_dump(ifa_json, default_flow_style=False)
            return render_template('descriptor.html', html_title='Descriptor Viewer',
                                   descriptor_type=descriptor_type,
                                   yaml_network=osm_json_network,
                                   list_osm_json=list_osm_json,
                                   yaml_osm_descriptor=yaml_descriptor_list,
                                   yaml_ifa_descriptor=yaml_ifa_descriptor,
                                   ifa_json=ifa_json,
                                   already_onboarded_in_so=already_onboarded_in_so)
        except (TypeError, KeyError, ValueError) as error:
            message = {'Error': 'Error: {}'.format(error)}
            log_queue.put(["ERROR", message['Error']])
            flash(message['Error'], 'danger')
            return redirect(url_for('home'))
            # return render_template('ifa_conv.html', html_title='IFA Converter')


@app.route('/ns_view/<string:ns_id>')
@login_passed
def ns_view(ns_id):
    # get the nsdId that corresponds to nsId
    nsd_id = ns_db.get_nsdId(ns_id)
    domain = nsd_db.get_nsd_domain(nsd_id)
    nsd_json = nsd_db.get_nsd_json(nsd_id)
    flavour_id = ns_db.get_ns_flavour_id(ns_id)
    ns_instantiation_level_id = ns_db.get_ns_instantiation_level_id(ns_id)
    # print("Fla/inst_level: {} {}".format(flavour_id, ns_instantiation_level_id))
    placement_info = None
    # print("Placement_info", placement_info)
    ns_network = {}
    level = "{}_{}_{}".format(nsd_id, flavour_id, ns_instantiation_level_id)
    if domain == 'local':
        html_page = 'ns_view.html'
        placement_info = nsir_db.get_placement_info(ns_id)
        list_osm_json, default_index = gui_utils.ifa014_conversion(nsd_json)
        for element in list_osm_json:
            if element['nsd:nsd-catalog']['nsd'][0]['id'] == level:
                ns_network = gui_utils.json_network_nsd(element, placement_info)
    elif domain == 'Composite':
        html_page = 'ns_composite_view.html'
        list_osm_json, default_index = gui_utils.composite_desc_conversion(nsd_json)
        for element in list_osm_json:
            if element['nsd:nsd-catalog']['nsd-composite'][0]['id'] == level:
                ns_network = gui_utils.json_network_composite_ns(element, ns_id)
    else:
        message = {'Error': 'Error: Something Wrong with domain of Descriptor'}
        log_queue.put(["ERROR", message['Error']])
        flash(message['Error'], 'danger')
        return redirect(request.referrer)
    return render_template(html_page,
                           html_title=ns_db.get_ns_name(ns_id),
                           d3_network=json_graph.node_link_data(ns_network))


def main():
    # logger.info("Starting NBI server :)")
    log_queue.put(["INFO", "Starting NBI server :)"])
    # set_start_method('spawn')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api("swagger.yaml", arguments={"title": "5GT-SO NBI"})
    app.add_url_rule("/sla_manager/notifications", view_func=SLAManagerAPI.as_view('SLA Manager'))
    app.app.secret_key = "secret"
    app.app.permanent_session_lifetime = timedelta(minutes=30)  # to activate expiring session(uncomment also in login)
    app.run(port=so_port, threaded=True)


if __name__ == "__main__":
    main()
