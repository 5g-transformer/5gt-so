FROM python:3.5-alpine

### All this just to build OSMClient
RUN apk add git
RUN apk add curl-dev
RUN apk add gcc
RUN apk add libmagic
RUN apk add musl-dev
###

RUN mkdir -p /usr/src/app


COPY requirements.txt /usr/src/app/

RUN pip3 install --no-cache-dir -r /usr/src/app/requirements.txt

RUN pip install git+https://osm.etsi.org/gerrit/osm/osmclient.git

COPY . /usr/src/app
WORKDIR /usr/src/app/nbi/python-flask-server
RUN sed -i 's/db.ip.*/db.ip=so_mongo/g' /usr/src/app/db/db.properties
ENV PYTHONPATH "${PYTHONPATH}:/usr/src/app:/usr/src/app/sm:/usr/src/app/nbi:/usr/src/app/db:/usr/src/app/coreMano:/usr/src/app/log:/usr/src/app/nbi/python-flask-server"

EXPOSE 8080

ENTRYPOINT ["python3"]

CMD ["-m", "swagger_server"]