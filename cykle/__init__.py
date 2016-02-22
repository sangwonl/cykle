from trello import TrelloApi
from prettytable import PrettyTable

import sys
import os
import shutil
import click
import re
import webbrowser


def load_cfg_vars_as_dict():
    sys.path.append(os.getcwd())
    import cyklecfg
    return {
        'trello_apikey': getattr(cyklecfg, 'TRELLO_APIKEY'),
        'trello_token': getattr(cyklecfg, 'TRELLO_TOKEN'),
        'trello_org': getattr(cyklecfg, 'TRELLO_ORG'),
        'trello_board_id': getattr(cyklecfg, 'TRELLO_BOARD_ID'),
        'github_owner': getattr(cyklecfg, 'GITHUB_OWNER'),
        'github_repo': getattr(cyklecfg, 'GITHUB_REPO')
    }


@click.group()
@click.pass_context
def cli(ctx):
    pass


@cli.command(name='init-cykle')
@click.pass_context
def init_cykle(ctx):
    try:
        cfgfile = open('cyklecfg.py', 'r')
    except IOError:
        pass
    else:
        print 'Cykle is already initialized'
        exit(0)

    # get trello api key
    trello_apikey = raw_input('Trello API Key: ')

    # get trello token
    trello_api = TrelloApi(trello_apikey)
    token_url = trello_api.get_token_url('Cykle', expires='30days', write_access=True)
    webbrowser.open(token_url)
    trello_token = raw_input('Trello Token: ')

    # get trello organization
    trello_orgnization = raw_input('Trello Organization: ')

    # get trello board id
    trello_board_name = raw_input('Trello Board Name: ')
    trello_api = TrelloApi(trello_apikey, trello_token)
    boards = trello_api.organizations.get_board(trello_orgnization)
    for b in boards:
        if b['name'] == trello_board_name:
            trello_board_id = b['id']

    # github repository info
    github_owner_name = raw_input('Github Owner Name: ')
    github_repository = raw_input('Github Repository: ')

    # generate cykle config file
    print 'generating cykle config file...'
    cfgtext_templ = \
        "TRELLO_APIKEY = '%s'\n" + \
        "TRELLO_TOKEN = '%s'\n" + \
        "TRELLO_ORG = '%s'\n" + \
        "TRELLO_BOARD_ID = '%s'\n" + \
        "GITHUB_OWNER = '%s'\n" + \
        "GITHUB_REPO = '%s'\n"

    cfgtext = cfgtext_templ % (
        trello_apikey,
        trello_token,
        trello_orgnization,
        trello_board_id,
        github_owner_name,
        github_repository
    )

    cfgfile = open('cyklecfg.py', 'w')
    cfgfile.write(cfgtext)

    # put pre-push under ./.git/hooks/
    print 'copy pre-push to .git/hooks/pre-push...'
    this_dir, this_file = os.path.split(__file__)
    src_file = os.path.join(this_dir, 'data', 'pre-push')
    dst_dir = './.git/hooks'
    shutil.copy(src_file, dst_dir)


@cli.group()
@click.pass_context
def trello(ctx):
    ctx.obj.update(load_cfg_vars_as_dict())
    ctx.obj.update({'trello_api': TrelloApi(ctx.obj['trello_apikey'], ctx.obj['trello_token'])})


@trello.command(name='setup-board')
@click.pass_context
def setup_board(ctx):
    lists = ['to_do', 'in_progress', 'code_review', 'to_deploy', 'live_qa', 'closed']
    for l in reversed(lists):
        ctx.obj['trello_api'].lists.new(l, ctx.obj['trello_board_id'])


@trello.command(name='list-card')
@click.argument('list_name', default='')
@click.pass_context
def list_card(ctx, list_name):
    cards = ctx.obj['trello_api'].boards.get_card(ctx.obj['trello_board_id'])

    pt = PrettyTable(['card id', 'card name', 'list name', 'members'])
    pt.align['card id'] = 'l'
    pt.align['card name'] = 'l'
    pt.align['list name'] = 'l'

    list_map = {}
    member_map = {}
    for c in cards:
        # list info
        list_id = c['idList']
        the_list = list_map.get(list_id, None)
        if not the_list:
            the_list = ctx.obj['trello_api'].lists.get(c['idList'])
            list_map[list_id] = the_list

        if list_name and the_list['name'] != list_name:
            continue

        # member info
        member_names = []
        for mem_id in c['idMembers']:
            member = member_map.get(mem_id, None)
            if not member:
                member = ctx.obj['trello_api'].members.get(mem_id)
                member_map[mem_id] = member
            member_names.append(member['fullName'])

        pt.add_row([c['idShort'], c['name'], the_list['name'], ', '.join(member_names)])

    print pt


@trello.command(name='link-commit')
@click.argument('commit')
@click.argument('card_id', default=0)
@click.pass_context
def link_commit(ctx, commit, card_id):
    if card_id == 0:
        comps = commit.lower().split(' ')
        commit = comps[0]
        card_id = re.search(r'[0-9]+', comps[1]).group(0)
    
    card = ctx.obj['trello_api'].boards.get_card_idCard(card_id, ctx.obj['trello_board_id'])
    url_templ = 'https://github.com/{0}/{1}/commit/{2}'
    commit_url = url_templ.format(ctx.obj['github_owner'], ctx.obj['github_repo'], commit)

    ctx.obj['trello_api'].cards.new_action_comment(card['id'], commit_url)


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
