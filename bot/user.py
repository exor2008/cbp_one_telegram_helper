import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Union, Optional

from dataclasses_json import dataclass_json

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class TodayApp:
    email: str
    password: str
    code: str
    left: int


@dataclass_json
@dataclass
class Application:
    password: str
    codes: List[str]
    current_code: int = 0


@dataclass_json
@dataclass
class User:
    id: int
    name: str
    applications: Dict[str, Application]


class UserManager:
    def __init__(self, path: Union[Path, str]) -> None:
        self.path = path
        if not isinstance(path, Path):
            self.path = Path(self.path)

    def is_registered(self, user_id: str) -> bool:
        return str(user_id) in [path.stem for path in self.path.iterdir()]

    def register(self, user: User) -> None:
        self._write_user(user)
        logger.info(f"User registered name: {user.name} id: {user.id}")

    def add_application(
        self, user_id: str, email: str, application: Application
    ) -> None:
        json_user = self._read_user(user_id)

        user = User.schema().loads(json_user)
        user.applications[email] = application

        self._write_user(user)

    def get_today_app(self, user_id: str, email: str) -> TodayApp:
        json_user = self._read_user(user_id)

        user = User.schema().loads(json_user)
        app = user.applications.get(email)

        if app.current_code >= len(app.codes):
            today_app = TodayApp(email, "", "", 0)
        else:
            left = len(app.codes) - app.current_code - 1
            today_app = TodayApp(email, app.password, app.codes[app.current_code], left)

            app.current_code += 1

        self._write_user(user)

        return today_app

    def get_emails(self, user_id: str) -> List[str]:
        json_user = self._read_user(user_id)

        user = User.schema().loads(json_user)

        return list(user.applications.keys())

    def create_user(self, user_id: str, name: str) -> User:
        return User(user_id, name, {})

    def create_application(self, password: str, codes: List[str]) -> Application:
        return Application(password, codes)

    def _read_user(self, user_id: str) -> str:
        with open(self.path / f"{user_id}.json") as f:
            json_user = f.read()

        return json_user

    def _write_user(self, user: User) -> None:
        with open(self.path / f"{user.id}.json", mode="w") as f:
            f.write(user.to_json(indent=4))


if __name__ == "__main__":
    m = UserManager(Path(r"D:\code\cbp_one\users"))
    a = 0
