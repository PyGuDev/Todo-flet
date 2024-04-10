import os
import uuid
from datetime import datetime
from http import HTTPStatus
from uuid import UUID

import aiopg
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel


connection_poll: aiopg.Pool
pg_dsn = os.environ.get("PG_DSN", "postgresql://username:password@localhost:5439/lab")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global connection_poll
    connection_poll = await aiopg.create_pool(pg_dsn)
    yield
    connection_poll.close()


app = FastAPI(
    title="Интернет программирование",
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan
)


class Task(BaseModel):
    id: UUID
    text: str
    created_at: datetime | None


class TaskText(BaseModel):
    text: str


@app.get("/api/task", response_model=list[Task], status_code=HTTPStatus.OK)
async def get_task():
    query = "select id, text, created_at from task"
    async with connection_poll.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query)
            result = [Task(id=item[0], text=item[1], created_at=item[2]) for item in await cur.fetchall()]

    return result


@app.post("/api/task", response_model=Task, status_code=HTTPStatus.CREATED)
async def create_task(
    text: TaskText
):
    insert_data = (str(uuid.uuid4()), text.text, datetime.now())

    async with connection_poll.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("begin")
            query = "insert into task (id, text, created_at) values (%s, %s, %s)"
            await cur.execute(query, insert_data)
            await cur.execute("commit")
            return Task(id=insert_data[0], text=insert_data[1], created_at=insert_data[2])


@app.put("/api/task/{task_id}", response_model=Task, status_code=HTTPStatus.OK)
async def update_task(
    task_id: str,
    text: TaskText
):
    update_data = (text.text, task_id)
    query = "update task set text=(%s) where id=(%s)"
    async with connection_poll.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("begin")
            await cur.execute(query, update_data)
            await cur.execute("select id, text, created_at from task where id=(%s)", (task_id,))
            data = await cur.fetchone()
            await cur.execute("commit")
            if data:
                return Task(id=str(data[0]), text=data[1], created_at=data[2])


@app.delete("/api/task/{task_id}", status_code=HTTPStatus.OK)
async def delete_task(
    task_id: str
):
    query = "delete from task where id=(%s)"
    async with connection_poll.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("begin")
            await cur.execute(query, (task_id,))
            await cur.execute("commit")
            return {"msg": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
