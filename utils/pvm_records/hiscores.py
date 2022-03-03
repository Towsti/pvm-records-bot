from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class Entry:
    id: int
    rank: int
    name: str
    score: int
    first_places: int
    second_places: int
    third_places: int

    def is_hiscores_leader(self):
        """Check if the entry is rank 1

        :return: entry is rank 1 (True), any other rank (False)
        :rtype: bool
        """
        return True if self.rank == 1 else False

    def first_best(self):
        """Check if the best placement for the entry is a first place.

        :return: best place is first (True), best place is 2nd, 3rd or lower (False)
        :rtype: bool
        """
        return True if self.first_places >= 1 else False

    def second_best(self):
        """Check if the best placement for the entry is a first place.

        :return: best place is first (True), best place is 2nd, 3rd or lower (False)
        :rtype: bool
        """
        return True if self.first_places == 0 and self.second_places >= 1 else False

    def third_best(self):
        """Check if the best placement for the entry is a third place.

        :return: best place is third (True), best place is 1nd, 2rd or lower than 3rd (False)
        """
        return True if self.first_places == 0 and self.second_places == 0 and self.third_places >= 1 else False


class Hiscores:
    ENDPOINT = "http://pvm-records.com/v1/leaderboard"

    def __init__(self):
        self.entries = list()

    def __request_hiscores(self):
        """Request the most recent version of the hiscores page.

        :return: request response as a list of entries
        :rtype: list[dict]
        """
        data = None
        try:
            response = requests.get(Hiscores.ENDPOINT)
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        else:
            if response.status_code == 200:
                data = response.json()
            else:
                print(f"Request error, status code: {response.status_code}")
        finally:
            return data

    def refresh(self):
        """Refresh the hiscores entries with the latest version of pvm-records/hiscores.
        The entries are only updated on a successful refresh.

        :return: refresh successful (True), refresh failed (False)
        :rtype: bool
        """
        data = self.__request_hiscores()
        if data:
            self.entries = [Entry(**entry) for entry in data]
            refreshed = True
        else:
            refreshed = False

        return refreshed

    def get_entry_by_name(self, name):
        """Search for a specifc hiscores entry using the name.

        :param str name: name (rsn) of the entry to search for
        :return: a single entry containing the name and other stats or an empty entry when the name isn't found.
        :rtype: Entry
        """
        return next((entry for entry in self.entries if entry.name == name),
                    Entry(0, 0, name, 0, 0, 0, 0))
