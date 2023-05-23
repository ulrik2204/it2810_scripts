import csv
import sys
from dataclasses import dataclass

import requests


@dataclass
class ContextParams:
    private_token: str
    parent_group_id: str


class Urls:
    GROUPS = "https://gitlab.stud.idi.ntnu.no/api/v4/groups/"

    @staticmethod
    def user_by_username(username: str):
        return f"https://gitlab.stud.idi.ntnu.no/api/v4/users?username={username}"

    @staticmethod
    def group_members(group_id: str):
        return f"https://gitlab.stud.idi.ntnu.no/api/v4/groups/{group_id}/members/"


def create_subgroup_from_api(private_token: str, group_name: str, parent_group_id: str):
    return requests.post(
        Urls.GROUPS,
        json={
            "parent_id": parent_group_id,
            "name": group_name,
            "path": "-".join(group_name.split(" ")),
        },
        headers={"PRIVATE-TOKEN": private_token},
    ).json()


def add_user_to_group_from_api(private_token: str, user_id: str, group_id: str):
    return requests.post(
        Urls.group_members(group_id),
        headers={
            "PRIVATE-TOKEN": private_token,
            "content-type": "application/x-www-form-urlencoded",
        },
        data=f"user_id={user_id}&access_level=40",
    )


def get_user_id_from_api(private_token: str, username: str) -> str | None:
    try:
        return requests.get(
            Urls.user_by_username(username),
            headers={"PRIVATE-TOKEN": private_token},
        ).json()[0]["id"]
    except Exception:
        print("could not find id for", username)
        return None


def read_csv(path: str) -> list[list[str]]:
    arr = []
    with open(path, newline="") as file:
        s = csv.reader(file)
        for row in s:
            arr.append(row)
    return arr


def map_usernames_to_ids(context: ContextParams, usernames: list[str]):
    user_ids = []
    for username in usernames:
        if username == "":
            continue
        user_id = get_user_id_from_api(context.private_token, username)
        if user_id is not None:
            user_ids.append(user_id)
    return user_ids


def create_groups_dict(
    context_params: ContextParams, groups_arr: list[list[str]]
) -> dict[str, list[str]]:
    dic = {}
    for group in groups_arr:
        team_nr = group[0]
        if team_nr == "":
            continue
        team_name = f"Team {team_nr}"
        members = map_usernames_to_ids(context_params, group[1:5])
        dic[team_name] = members
    return dic


def create_gitlab_groups(context: ContextParams, groups_dict: dict[str, list[str]]):
    for group_name in groups_dict:
        created_group = create_subgroup_from_api(
            context.private_token, group_name, context.parent_group_id
        )
        print("created_group", created_group)
        created_group_id = created_group["id"]
        # Add members to group
        member_ids = groups_dict[group_name]
        for member_id in member_ids:
            res = add_user_to_group_from_api(
                context.private_token, member_id, created_group_id
            )
            if not res.ok:
                print(f"Request to add {member_id} to {group_name} failed.")


def main():
    if len(sys.argv) < 3:
        return print(
            "Requires 3 arguments: private_token group_id groups_csv_file_path"
        )

    _, private_token, group_id, groups_path = sys.argv
    context_params = ContextParams(private_token, group_id)
    # print(read_csv("groups.csv"))
    print(private_token, group_id, groups_path)
    # Parse the csv file to array
    groups_arr = read_csv(groups_path)
    # Crease a dictionary of the team name (Team NR) and a list of IDs
    groups = create_groups_dict(context_params, groups_arr[1:])
    print(groups)
    # Create the groups on GitLab
    create_gitlab_groups(context_params, groups)


if __name__ == "__main__":
    main()
