# from enum import unique
# from logging import error
# import os
# from nltk.sem.evaluate import Error
# import urllib.parse
from databases import DatabaseURL
from pymongo import MongoClient, errors
from pydantic.types import UUID4


# from pymongo.common import TIMEOUT_OPTIONS

class MongoAPI:
    def __init__(self, data):
        print("trying to connect")
        user = data['user']
        password = data['password']
        host = data['host']
        port = data['port']
        database = data['database']
        collection = data['collection']

        MONGODB_URL = str(DatabaseURL(
            f"mongodb://{user}:{password}@{host}:{port}"))
        print(MONGODB_URL)

        self.client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=10000, uuidRepresentation='standard')

        cursor = self.client[database]
        self.collection = cursor[collection]
        self.data = data
        try:
            self.collection.create_index([("guid", 1)], unique=True)
            self.collection.create_index([("fuzzy", "text")], default_language='english')
        except errors.PyMongoError as error:
            print(error)
            pass
        # self.collection.create_index([("title" , "text"),("body", "text")],name="match", default_language='english')

    def read(self, guid):
        documents = self.collection.find({'guid': guid})
        output = [{item: data[item] for item in data if item != '_id'} for data in documents]
        return output

    def fetch(self, query):
        if 'guid' in query:
            query['guid'] = UUID4(query['guid'])
        documents = self.collection.find(query)
        print("db.FETCH", documents)
        output = [{item: data[item] for item in data if item != '_id'} for data in documents]
        return output

    def create(self, data):
        data['guid'] = data['guid']
        response = self.collection.insert_one(data)

        return data['guid'], response.acknowledged

    def delete(self, guid):
        response = self.collection.delete_one({'guid': guid})
        return response.deleted_count

    def search(self, text, fuzzy, limit, threshold, user_id=None):
        if fuzzy:
            match = {"$and": [{"user_id": user_id}, {"$text":
                {
                    "$search": text,
                    "$caseSensitive": False,
                    "$diacriticSensitive": False
                }
            }]}
            match = match if user_id else match['$and'][1]
            query = [{"$match": match}
                ,
                     {"$project":
                         {
                             "score": {"$meta": "textScore"},
                             "guid": 1,
                             "user_id": 1,
                             "title": 1,
                             "body": 1,
                             "data": 1
                         }},
                     {"$match": {"score": {"$gt": threshold}}},
                     {"$sort": {"score": 1}},
                     {"$limit": limit}
                     ]
            print("QUERY (aggregate):", query)
            documents = self.collection.aggregate(query)
        else:
            query = {"$or": [{"title": {"$regex": text}}, {"body": {"$regex": text}}]}
            if user_id:
                query = {"$and": [{"user_id": user_id}, query]}
            print("QUERY (find):", query)
            documents = self.collection.find(query,
                                             {
                                                 "guid": 1,
                                                 "user_id": 1,
                                                 "title": 1,
                                                 "body": 1,
                                                 "data": 1
                                             }).limit(limit)
        # documents = self.collection.find({
        #     "$or":[
        #         {"title":text},
        #         {"body":text}
        #         ]})
        output = [{item: data[item] for item in data if item != '_id'} for data in documents]

        return output
