import json
import os


class UserSettingsControl:
    JSON_FILE = 'user_settings.json'

    def __init__(self):
        self.__settings = dict()
        self.__load_json()

    @property
    def settings(self):
        return self.__settings

    def update(self, user_id, name):
        self.__settings[user_id] = name
        self.__update_json()

    def remove(self, user_id):
        removed_name = self.__settings.pop(user_id)
        self.__update_json()
        return removed_name

    def __load_json(self):
        if os.path.isfile(UserSettingsControl.JSON_FILE):
            with open(UserSettingsControl.JSON_FILE, 'r') as file:
                self.__settings = json.load(file)
        else:
            self.__settings = dict()

    def __update_json(self):
        with open(UserSettingsControl.JSON_FILE, 'w') as file:
            json.dump(self.__settings, file)
