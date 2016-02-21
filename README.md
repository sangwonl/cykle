### Installation
```
$ pip install cykle
```

### Initialization
```
$ cd <your-git-repo-home>
$ python cykle.py init-cykle
Trello API Key: <your-trello-key>     # https://trello.com/app-key
Trello Token: <your-trello-token>     # can get from opening browser that it opens
Trello Organization: <your-trello-org-name>
Trello Board Name: <your-trello-board-name>
Github Owner Name: <your-github-owner-name>
Github Repository: <your-github-repo-name>

$ python cykle.py trello setup-board
```

### CLI Usage
#### List Cards
```
$ python cykle.py list-card
+---------+------------------+-------------+-------------+
| card id | card name        | list name   |   members   |
+---------+------------------+-------------+-------------+
| 2       | Update README.md | to_do       | Sangwon Lee |
| 1       | Upload to github | code_review | Sangwon Lee |
+---------+------------------+-------------+-------------+
```

#### Link Commit to Card
```
$ python cykle.py 0a444de0bfa0ff54e94623790076d8c9dd93f873 2

or

$ python cykle.py "$(git log -1 --oneline HEAD)" 1
```

### Setup with post-commit
- Download `post-commit` and copy it into .git/hooks
- When you commit the changes, put the prefix(`issue#<card-id>`) at the head of message like:
```
git commit -m "issue#2: your commit message"
```