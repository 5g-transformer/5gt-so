from flask import Flask
from flask import *
from PASchema import PAreq, PAreqSchema
from PAdist import PAdist
from PAlatency import PAlatency


app = Flask(__name__)

PArequests = []


@app.route('/5gt/so/v1/PAComp', methods=['GET'])
@app.route('/5gt/so/v1/PAComp<int:path_id>', methods=['GET'])
# def index():
#	return "hello world!"
# def get_tasks():
#	return jsonify({'tasks':tasks})
# def  get_tasks(task_id=None):
# 	if task_id:
# 		task=[task for task in tasks if task['id']==task_id]
# 		if len(task)==0:
# 			abort(404)
# 		return jsonify({'task':task[0]})
# 	else:
# 		return jsonify({'tasks':tasks})
@app.route('/5gt/so/v1/PAComp', methods={'POST'})
def create_paths():
    if not request.json:
        abort(400)

    PArequest = PAreqSchema()
    inputReq = PArequest.load(request.json)
    # PArequests.append(inputReq)
    for key in inputReq.keys():
        if key == "nfvi":
            for key1 in inputReq[key].keys():
                if key1 == "LLs":
                    LLs = inputReq[key][key1]
                if key1 == "NFVIPoPs":
                    NFVIPoP = inputReq[key][key1]
    # for key in inputReq.keys():
        if key == "nsd":
            NSD = inputReq[key]
    response = PAdist(NFVIPoP, LLs, NSD)
    # response=PAlatency(NFVIPoP,LLs,NSD)
    if response:
        print response
        PArequests.append(response)
        i = len(PArequests)
        return jsonify({'response': PArequests[i - 1]}), 201

    else:
        abort(404)

# @app.route('/python_rest/server/v1.0/sum', methods={'POST'})
# def sum():
# 	if not request.json or not 'data1' in request.json or not 'data2' in request.json:
# 		abort(400)
# 	datas= {

# 		'data1':request.json['data1'],
# 		'data2':request.json['data2'],
# 	}
# 	data1=int(datas.values()[0])
# 	data2=int(datas.values()[1])
# 	summa=data1+data2
# 	tasks.append(summa)
# 	return jsonify({'summa':summa}),201


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


if __name__ == '__main__':
    app.run(debug=True, port=8081)
