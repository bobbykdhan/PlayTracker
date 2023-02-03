

FROM docker.io/python:3.8-buster


LABEL maintainer="Bobby Dhanoolal <>bobbydhanoolal@gmail.com>" tag="Discord Bot"
#
#ARG ssh_prv_key
#
## Add the keys and set permissions
#RUN echo "$ssh_prv_key" > /root/.ssh/id_rsa && \
#    chmod 600 /root/.ssh/id_rsa &&
COPY ./test.sh /test.sh

RUN chmod 777 test.sh

WORKDIR /app
ADD ./ /app
COPY ./requirements.txt requirements.txt
RUN apt-get -yq update && \
    pip install --no-cache-dir -r requirements.txt

COPY . .


WORKDIR /app/

CMD ["python3", "main.py"]