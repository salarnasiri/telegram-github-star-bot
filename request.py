import requests



class GithubRequest:
    def __init__(self, base_url="https://api.github.com"):
        self.base_url = base_url
        self.headers = {
            'Cache-Control': "no-cache",
            'Content-Length': '0'
        }

    def get_user_by_token(self, token):
        url = self.base_url + "/" + "user"
        headers = self.headers
        headers["Authorization"] = "Bearer " + token

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()["login"], True
        else:
            return response.json()["message"], False

    def set_star_by_token(self, token, repo_owner, repo_name):
        url = self.base_url + "/" + "user/starred/" + repo_owner + "/" + repo_name
        headers = self.headers
        headers["Authorization"] = "Bearer " + token
        response = requests.put(url, headers=headers)
        if response.status_code == 204:
            return True
        else:
            return False
