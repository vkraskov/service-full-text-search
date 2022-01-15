import os
from typing import Optional

import fuzzy
import nltk
# from starlette.responses import Response
import uvicorn
from fastapi import FastAPI, HTTPException, status
# import re
from fonetika.soundex import RussianSoundex
from nltk import word_tokenize
from nltk.corpus import stopwords
from pydantic import BaseModel
# from nltk.sem.evaluate import Error
from pydantic.types import UUID4
from pymongo import errors

from MongoAPI import MongoAPI

soundex = RussianSoundex(delete_first_letter=True, code_vowels=True)

data = {
    "database": os.environ['DB_DATABASE'],
    "collection": "photos",
    "user": os.environ['DB_USER'],
    "password": os.environ['DB_PASSWORD'],
    "host": os.environ['DAT_HOST'],
    "port": os.environ['DAT_PORT'],
}
try:
    db = MongoAPI(data)
except errors.AutoReconnect as error:
    print("Conniction to Database failed")
    print("Message : ", error._message)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database Unavilable ")
except errors.PyMongoError as error:
    print("Message: ", error._message)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database Unavilable ")

nltk.download('punkt')
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

app = FastAPI(title='TEXT SEARCH API')


class Document(BaseModel):
    guid: UUID4
    user_id: str
    title: str
    body: str
    data: dict
    fuzzy: Optional[str] = None


class FetchQuery(BaseModel):
    query: dict


class SearchQuery(BaseModel):
    query: str
    user_id: Optional[str] = None
    limit: Optional[int] = 10
    threshold: Optional[float] = 0.6
    fuzzy: Optional[bool] = True


@app.get('/')
async def base():
    # return Response(response=js_dumps({"Status": "UP"}),
    #                 status=200,
    #                 mimetype='application/json')
    return {"Status": "UP"}


@app.get('/api/doc/read/{guid}')
async def mongo_read(guid: UUID4):
    print("READ", guid)
    try:
        response = db.read(guid)
    except errors.PyMongoError as error:
        print(error._message)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Connection error")

    if response is None or response == []:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found!")
    return response


@app.get('/api/doc/fetch')
async def mongo_fetch(document: FetchQuery, status_code=201):
    print("FETCH", document.query)
    try:
        response = db.fetch(document.dict()['query'])
    except errors.PyMongoError as error:
        print(error._message)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Connection error")

    if response is None or response == []:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found!")
    return response


@app.post('/api/doc/create')
async def mongo_create(document: Document, status_code=201):
    document.fuzzy = fill_fuzzy(document.title, document.body)
    try:
        guid, sucsess = db.create(document.dict())
    except errors.DuplicateKeyError as error:
        print(error._message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document already exists")
    except errors.WriteError as error:
        print(error._message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Write error")
    except errors.PyMongoError as error:
        print(error._message)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Connection error")
    response = {'Status': 'Successfully Inserted',
                'guid': guid}
    return response


def clear(words):
    # words = re.sub(r'\d+', '', words)
    words = word_tokenize(words)
    # words= [word for word in words if word.isalnum() and word.lower() not in stop_words]
    return words


def fuzzy_text(text):
    f = ""
    for word in text:
        ss = fuzzy.nysiis(word)
        if ss == '':
            ss = soundex.transform(word)
        if ss != '':
            f = f + " " + ss
    return f


def fill_fuzzy(title, body):
    body = clear(body)
    title = clear(title)
    f = fuzzy_text(title) + fuzzy_text(body)
    return f


@app.delete('/api/doc/delete/{guid}')
def mongo_delete(guid: UUID4):
    try:
        delete_cout = db.delete(guid)
        if delete_cout == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found!")
        return {'deleted': guid}
    except errors.WriteError as error:
        print(error._message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document already exists")
    except errors.PyMongoError as error:
        print(error._message)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Connection error")


@app.get('/api/doc/search')
async def mongo_search(q: SearchQuery):
    search_text = ""
    if q.fuzzy:
        search_text = fuzzy_text(clear(q.query))
        print("Search text (fuzzy) = ", search_text)
    else:
        for i in clear(q.query):
            search_text = search_text + "(?=.*" + i + ")"
        print("Search text = ", search_text)
        # search_text=q.query
    try:
        res = db.search(search_text, q.fuzzy, q.limit, q.threshold, q.user_id)
    except errors.PyMongoError as error:
        print(error._message)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Connection error")

    # print(a)
    print(res)

    return res


if __name__ == '__main__':
    uvicorn.run('app:app', debug=True, reload=True, port=int(os.environ['APP_PORT']), host=os.environ['APP_HOST'])
