import os

import flet as ft
import httpx
import logging


ADDRESS_BACKEND = os.environ.get("ADDRESS_BACKEND", "http://localhost:8000")


class ApiClient:
    def __init__(self):
        self._client = httpx.AsyncClient()

    async def get_task(self):
        response = await self._client.get(f"{ADDRESS_BACKEND}/api/task")
        return response.json()

    async def delete_task(self, task_id: str):
        response = await self._client.delete(f"{ADDRESS_BACKEND}/api/task/{task_id}")
        return response.json()["msg"] == "ok"

    async def create_task(self, text: str) -> dict:
        data = {"text": text}
        response = await self._client.post(f"{ADDRESS_BACKEND}/api/task", json=data)
        return response.json()

    async def update_task(self, task_id: str, text: str) -> dict:
        data = {"text": text}
        response = await self._client.put(f"{ADDRESS_BACKEND}/api/task/{task_id}", json=data)
        return response.json()


class Task(ft.UserControl):
    def __init__(self, payload, client: ApiClient, task_delete):
        super().__init__()
        self.completed = False
        self.client = client
        self.task_delete = task_delete
        self.payload = payload
        self.task_name = self.get_task_name()

    def get_task_name(self):
        return self.payload['text']

    def build(self):
        self.display_task = ft.Checkbox(
            value=False, label=self.task_name, on_change=self.status_changed
        )
        self.edit_name = ft.TextField(expand=1)

        self.display_view = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.display_task,
                ft.Row(
                    spacing=0,
                    controls=[
                        ft.IconButton(
                            icon=ft.icons.CREATE_OUTLINED,
                            tooltip="Редактировать задачу",
                            on_click=self.edit_clicked,
                        ),
                        ft.IconButton(
                            ft.icons.DELETE_OUTLINE,
                            tooltip="Удалить задачу",
                            on_click=self.delete_clicked,
                        ),
                    ],
                ),
            ],
        )

        self.edit_view = ft.Row(
            visible=False,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.edit_name,
                ft.IconButton(
                    icon=ft.icons.DONE_OUTLINE_OUTLINED,
                    icon_color=ft.colors.GREEN,
                    tooltip="Редактировать задачу",
                    on_click=self.save_clicked,
                ),
            ],
        )
        return ft.Column(controls=[self.display_view, self.edit_view])

    async def edit_clicked(self, e):
            self.edit_name.value = self.display_task.label
            self.display_view.visible = False
            self.edit_view.visible = True
            await self.update_async()

    async def save_clicked(self, e):
        if data := await self.client.update_task(self.payload["id"], self.edit_name.value):
            self.display_task.label = data["text"]
            self.display_view.visible = True
            self.edit_view.visible = False
            await self.update_async()

    async def status_changed(self, e):
        self.completed = self.display_task.value
        await self.task_status_change(self)

    async def delete_clicked(self, e):
        await self.task_delete(self)


class TodoApp(ft.UserControl):

    def build(self):
        self.client = ApiClient()

        self.new_task = ft.TextField(
            hint_text="Что хотите сделать?", on_submit=self.add_clicked, expand=True
        )
        self.tasks = ft.Column()

        self.filter = ft.Tabs(
            scrollable=False,
            selected_index=0,
            tabs=[ft.Tab(text="all")],
        )

        self.items_left = ft.Text("0 items")

        return ft.Column(
            width=600,
            controls=[
                ft.Row(
                    [ft.Text(value="Todos", style=ft.TextThemeStyle.HEADLINE_MEDIUM)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        self.new_task,
                        ft.FloatingActionButton(
                            icon=ft.icons.ADD, on_click=self.add_clicked
                        ),
                    ],
                ),
                ft.Column(
                    spacing=25,
                    controls=[
                        self.filter,
                        self.tasks,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                self.items_left,
                            ],
                        ),
                    ],
                ),
            ],
        )

    def did_mount(self):
        self.page.run_task(self.update_task_list)

    async def add_clicked(self, e):
        if self.new_task.value:
            data = await self.client.create_task(self.new_task.value)
            task = Task(data, self.client, self.task_delete)
            self.tasks.controls.append(task)
            self.new_task.value = ""
            await self.new_task.focus_async()
            await self.update_async()

    async def task_delete(self, task):
        if await self.client.delete_task(task.payload["id"]):
            self.tasks.controls.remove(task)
            await self.update_async()

    async def update_async(self):
        count = 0
        for _ in self.tasks.controls:
            count += 1
        self.items_left.value = f"{count} items"
        await super().update_async()

    async def update_task_list(self):
        for item in await self.get_task():
            task = Task(item, self.client, self.task_delete)
            self.tasks.controls.append(task)
            self.new_task.value = ""
            await self.new_task.focus_async()
            await self.update_async()

    async def get_task(self) -> list:
        return await self.client.get_task()


async def main(page: ft.Page):
    page.title = "ToDo App"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.add(TodoApp())


ft.app(main)
