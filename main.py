import random

import uvicorn as uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()



class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

class ItemWithId(Item):
    id: str

@app.post("/items")
async def create_item(item: Item):
    itemWithId: ItemWithId = ItemWithId(
        name=item.name,
        description=item.description,
        price=item.price,
        tax=item.tax,
        id=random.randint(0,9)
    )
    return itemWithId

@app.get("/items/{item_id}")
async def read_item(item_id):
    return {"item_id": item_id}

@app.get("/")
async def root():
    return {"message": "Hello World"}
# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.




def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')
    uvicorn.run(app, host="127.0.0.1", port=8000)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
