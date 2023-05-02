import functools
import os

import motor.motor_asyncio
from typing import Union
from fastapi import FastAPI, Depends, requests, HTTPException, UploadFile
from pydantic import BaseModel
# from pymongo import MongoClient


app = FastAPI()
# client = MongoClient()


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


MONGO_URL = os.getenv('MONGO_URL') or "mongodb://root:example@mongo:27017"


@functools.lru_cache()
def mongo_data_collection():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db = client["data"]
    collection = db["verdicts"]
    return collection


@app.post("/events")
async def events(event: Event, mongo_collection=Depends(mongo_data_collection)) -> EventsResponse:
    data = await mongo_collection.find_one({"hash": event.file.file_hash})
    if not data:
        file_verdict = Verdict(hash=event.file.file_hash, risk_level=-1)
    else:
        file_verdict = Verdict(hash=event.file.file_hash, risk_level=data["risk_level"])

    data = await mongo_collection.find_one({"hash": event.last_access.hash})
    if not data:
        process_verdict = Verdict(hash=event.last_access.hash, risk_level=-1)
    else:
        process_verdict = Verdict(hash=event.last_access.hash, risk_level=data["risk_level"])
    return EventsResponse(file=file_verdict, process=process_verdict)


@app.post("/scan_file/")
async def upload(file: UploadFile, mongo_collection=Depends(mongo_data_collection)) -> Verdict:
    file_content = await file.read()

    url = "https://beta.nimbus.bitdefender.net/liga-ac-labs-cloud/blackbox-xcanner/"
    try:
        black_box_api_response = requests.post(url, files={"file": ("file.txt", file_content)}).json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    md5 = black_box_api_response['hash']
    risk_level = black_box_api_response['hash']
    verdict = Verdict(hash=md5, risk_level=risk_level)
    await mongo_collection.insert_one(Verdict.dict())
    print(f'Item created, {verdict=}')
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
