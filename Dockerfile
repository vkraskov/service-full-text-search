FROM python:alpine3.15
RUN apk add gcc libc-dev
RUN apk add g++

WORKDIR /code
COPY ./requirments.txt /code/requirments.txt
#RUN /bin/sh -c pip install --no-cache-dir --upgrade -r requirments.txt
RUN pip install --no-cache-dir --upgrade -r requirments.txt  

COPY ./app /code/app
#RUN pip install fonetika
WORKDIR /code/app

EXPOSE $APP_PORT
CMD uvicorn app:app --host $APP_HOST --port $APP_PORT 
# # ENTRYPOINT [ " uvicorn " ," app:app "," --host "," $APP_HOST "," --port "," $APP_PORT " ]
# ENTRYPOINT ["uvicorn","app:app","--host",$APP_HOST,"--port",$APP_PORT]
