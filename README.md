### Installation
```
$ pip install cykle
```

### Initialization
```
$ cd <your-git-repo-home>
$ cykle init
Trello API Key: <your-trello-key>           # https://trello.com/app-key
Trello Token: <your-trello-token>           # can get from opening browser that it opens
Trello Organization: <your-trello-org-name> # you must be member of the organization
Trello List for IN PROGRESS: <your-trello-list-for-todo>
Trello List for CODE_REVIEW: <your-trello-list-for-code-review>
Trello List for CLOSED: <your-trello-list-for-closed>
Trello Board Name: <your-trello-board-name>
Github Owner Name: <your-github-owner-name>
Github Repository: <your-github-repo-name>
Github Username: <your-github-username>
Github Password: <your-github-password>     # two-factor is not supported yet
Develop Branch: master
generating cykle config file...

```

### Work Cycle with CLI
#### List Issues
```
$ cykle issues
+---------+------------------+-------------+-------------+
| card id | card name        | list name   |   members   |
+---------+------------------+-------------+-------------+
|       2 | Update README    | to_do       | Sangwon Lee |
|       1 | Upload to github | code_review | Sangwon Lee |
+---------+------------------+-------------+-------------+
```

#### Start Work
`cykle start [issue_id:required] '[branch_name:required]'`
```
$ cykle start 2 'Update README'
```

#### Pull Request
`cykle pr [--force=True:optional] [title:optional] [body:optional]`

```
$ cykle pr
```

#### Close Issue
`cykle close [issue_id:required] [delete_remote_branch:optional]`
```
$ cykle close 2 True
```

### Refresh Trello Token
```
$ cykle token
Trello Token: <your-trello-token>           # can get from opening browser that it opens
updating cykle config file...
```
