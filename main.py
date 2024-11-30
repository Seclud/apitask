import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from Parser import get_price
from starlette.concurrency import run_in_threadpool
from sqlmodel import Field, SQLModel, create_engine, Session, select

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

class Prices(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    cost: int

def get_async_session():
    sqlite_url = "sqlite+aiosqlite:///parser.db"
    engine = create_async_engine(sqlite_url)
    dbsession = async_sessionmaker(engine)
    return dbsession()

async def get_session():
    async with get_async_session() as session:
        yield session

SessionDep = Depends(get_session)

def create_db_and_tables():
    sqlite_url = "sqlite:///parser.db"
    engine = create_engine(sqlite_url)
    SQLModel.metadata.create_all(engine)

def convert_price_to_int(price_str: str) -> int:
    numeric_str = ''.join(char for char in price_str if char.isdigit())
    return int(numeric_str)

async def background_parser_async(session:Session):
    while True:
        print("Starting get price")
        data = await run_in_threadpool(get_price)
        for item in data:
            title, price = item['name'], item['price']
            price = convert_price_to_int(price)
            print(f"{title} - {price}")

            statement = select(Prices).where(Prices.name == title, Prices.cost == price)
            result = session.execute(statement)
            existing_item = result.scalar_one_or_none()

            if existing_item is None:
                db_item = Prices(name=title, cost=price)
                session.add(db_item)
                await session.commit()
                await session.refresh(db_item)
        await asyncio.sleep(60 * 60)

@app.get("/start_parser")
async def start_parser(background_tasks: BackgroundTasks, session: Session = SessionDep):
    #  asyncio.create_task(background_add_item())
    background_tasks.add_task(background_parser_async,session)
    return {}

@app.get("/prices")
async def read_prices(session: Session = SessionDep, offset: int = 0, limit: int = 100):
    statement = select(Prices).offset(offset).limit(limit)
    items = await session.scalars(statement)
    return items.all()

@app.get("/prices/{item_id}")
async def read_item(item_id: int, session: Session = SessionDep):
    price = await session.get(Prices, item_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    return price

@app.put("/prices/{item_id}")
async def update_item(item_id: int, data: Prices, session: Session = SessionDep):
    price_db = await session.get(Prices, item_id)
    if not price_db:
        raise HTTPException(status_code=404, detail="Price not found")
    price_data = data.model_dump(exclude_unset=True)
    price_db.sqlmodel_update(price_data)
    session.add(price_db)
    await session.commit()
    await session.refresh(price_db)
    return price_db

@app.post("/prices/create")
async def create_item(item: Prices, session: Session = SessionDep):
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item

@app.delete("/prices/{item_id}")
async def delete_item(item_id: int, session: Session = SessionDep):
    price = await session.get(Prices, item_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    await session.delete(price)
    await session.commit()
    return {"ok": True}