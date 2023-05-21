# ICPC México Scoreboard

## Installation

- Install `asdf` ([steps](https://asdf-vm.com/guide/getting-started.html)).

- Install all required dependencies:
```shell
sudo apt-get install libffi-dev build-essential
asdf plugin add python
asdf install
pip install -r requirements.txt
```

- If you see errors like `ModuleNotFoundError: No module named '_ctypes'` when installing the dependencies, re-install your Python:
```shell
asdf uninstall python
asdf install python
```

- Create the MySQL database:
```sql
CREATE DATABASE icpc_mexico_scoreboard CHARACTER SET utf8;
CREATE USER 'scoreboard'@'localhost' IDENTIFIED BY 'let-me-in';
GRANT ALL PRIVILEGES ON icpc_mexico_scoreboard.* TO 'scoreboard'@'localhost';
```

- Apply all database migrations:
```shell
python manage.py migrate
```
