import functools
import os

import motor.motor_asyncio
import redis
import requests
import aio_pika


from aio_pika import ExchangeType, DeliveryMode
from typing import Union

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
# from pymongo import MongoClient


MONGO_URL = os.getenv('MONGO_URL') or "mongodb://root:example@localhost:27017"


app = FastAPI()
# client = MongoClient()
redis_client = redis.Redis(host='redis', port=6379, db=0)
redis_client.set('a', 'b', )

Instrumentator().instrument(app).expose(app)


class Device(BaseModel):
    id: str
    os: str


class File(BaseModel):
    file_hash: str
    file_path: str


class Time(BaseModel):
    a: int
    b: int


class Process(BaseModel):
    hash: str
    path: str
    pid: str


class Event(BaseModel):
    device: Device
    file: File
    last_access: Process


class Result(BaseModel):
    hash: str
    risk_level: int


class Verdict(BaseModel):
    hash: str
    risk_level: int


class EventsResponse(BaseModel):
    file: Verdict
    process: Verdict


class Item(BaseModel):
    name: str
    description: Union[str, None] = None
    price: float
    tax: Union[float, None] = None
    tags: list[str] = []


@app.post("/items/")
async def create_item(item: Item) -> Item:
    return item


@app.get("/items/")
async def read_items() -> list[Item]:
    return [
        Item(name="Portal Gun", price=42.0),
        Item(name="Plumbus", price=32.0),
    ]


@functools.lru_cache()
def mongo_data_collection():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db = client["data"]
    collection = db["verdicts"]
    return collection


async def find_in_redis(md5: str):
    return redis_client.get(md5)


def post_in_redis(md5: str, data):
    redis_client.append(str, data)


async def rabbitmq_exchange():
    # Perform connection
    connection = await aio_pika.connect("amqp://user:bitnami@rabbitmq/")
    # Creating a channel
    channel = await connection.channel()
    return await channel.declare_exchange(
        "logs", ExchangeType.FANOUT, durable=True,
    )


logs_exchange = None


@app.post("/events/")
async def events(event: Event, mongo_collection=Depends(mongo_data_collection)) -> EventsResponse:
    response = {}

    global logs_exchange
    message = aio_pika.Message(
        event.json().encode(),
        delivery_mode=DeliveryMode.PERSISTENT,
    )
    await logs_exchange.publish(message, routing_key="test")

    for key, md5 in [('file', event.file.file_hash), ('process', event.last_access.hash)]:
        redis_result = find_in_redis(md5)
        if redis_result is None:
            data = await mongo_collection.find_one({"hash": event.file.file_hash})
            if data is not None:
                post_in_redis(md5, data)
        else:
            data = redis_result
        if data is not None:
            risk_level = data['risk_level']
        else:
            risk_level = -1

        response[key] = Verdict(hash=md5, risk_level=risk_level)

    return EventsResponse(**response)


@app.post("/scan_file/")
async def upload(file: UploadFile, mongo_collection=Depends(mongo_data_collection)) -> Verdict:
    file_content = await file.read()

    url = "https://beta.nimbus.bitdefender.net/liga-ac-labs-cloud/blackbox-scanner/"
    try:
        black_box_api_response = requests.post(url, files={"file": ("file.txt", file_content)}).json()
    except Exception as e:
        print(f'---->{e}')
        raise HTTPException(status_code=400, detail=str(e))

    md5 = black_box_api_response['hash']
    risk_level = black_box_api_response['risk_level']
    verdict = Verdict(hash=md5, risk_level=risk_level)
    await mongo_collection.insert_one(verdict.dict())
    print(f'Item created, {verdict=}')
    print(f'{risk_level}  ---  {md5}')
    return verdict


# @mongo_router.post("/", response_model=SaveToMongoResponse)
# async def save_to_mongo(
#     data_in: HashVerdict, mongo_collection=Depends(mongo_data_collection)
# ):
#     await mongo_collection.insert_one(data_in.dict())
#     return SaveToMongoResponse(message="Item created")
#
#
# @mongo_router.get("/{item_hash}", response_model=HashVerdict)
# async def get_from_mongo(
#     item_hash: str, mongo_collection=Depends(mongo_data_collection)
# ):
#     data = await mongo_collection.find_one({"hash": item_hash})
#     if not data:
#         raise HTTPException(statuscode=404, detail="Not Found")
#     return data


# @app.get("/scan_file")
# async def scan_file(event: Event):
#     verdict: Verdict = Verdict()
#     verdict.file.hash = event.file.file_hash
#     verdict.process.hash = event.last_access.hash
#     verdict.file.risk_level = -1
#     verdict.process.risk_level = -1
#     return verdict

if __name__ == "__main__":
    uvicorn.run(app)

# async await, blocking functions
