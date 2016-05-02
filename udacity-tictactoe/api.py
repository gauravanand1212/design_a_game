# -*- coding: utf-8 -*-`
"""api.py - TiTacToe Game API
Contains the endpoint methods to access the game and make moves.
Messaging system allows users to keep track of the tic tac toe
board. """


import logging
import endpoints
from google.appengine.api import taskqueue
from protorpc import remote, messages

from models import User, Game
from models import UserForms, ShowGamesForm, ShowGamesForms, RankingForm
from models import GameForm, NewGameForm, MakeMoveForm, StringMessage
from models import GameHistoryForm, GameHistoryForms

from utils import get_by_urlsafe

ALLOWED_CLIENTS = [endpoints.API_EXPLORER_CLIENT_ID]

CREATE_USER_REQUEST = endpoints.ResourceContainer(
    user_name=messages.StringField(1),
    email=messages.StringField(2))
USER_GAMES_REQUEST = endpoints.ResourceContainer(
  user_name=messages.StringField(1))
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
SHOW_GAME_REQUEST = endpoints.ResourceContainer(
  urlsafe_game_key=messages.StringField(1))

MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1))


@endpoints.api(name='tictactoe', version='v1',
               allowed_client_ids=ALLOWED_CLIENTS)
class TicTacToeApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=CREATE_USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(response_message=UserForms,
                      path='userstats',
                      name='get_users',
                      http_method='GET')
    def get_users(self, request):
        """Get a list of all users and their stats"""
        return UserForms(items=[user.to_form() for user in User.query()])

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='newgame',
                      name='create_new_game',
                      http_method='POST')
    def create_new_game(self, request):
        """Create a new tictactoe game between 2 players"""
        userX = User.query(User.name == request.userX).get()
        userO = User.query(User.name == request.userO).get()
        if not userX:
            raise endpoints.NotFoundException(
                'User {} does not exist'.format(request.userX))
        if not userO:
            raise endpoints.NotFoundException(
                'User {} does not exist'.format(request.userO))

        game = Game.new_game(userX.key, userO.key)
        game.put()

        return game.to_form('Game created. {} to play first'.format(
                                                    request.userX))

    @endpoints.method(request_message=SHOW_GAME_REQUEST,
                      response_message=GameForm,
                      path='showgame/{urlsafe_game_key}',
                      name='show_game',
                      http_method='GET')
    def show_game(self, request):
        """Show current game state"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Game details')
        else:
            endpoints.NotFoundException('Game not found. Enter valid key')

    @endpoints.method(request_message=SHOW_GAME_REQUEST,
                      response_message=GameHistoryForms,
                      path='showgamehistory/{urlsafe_game_key}',
                      name='show_game_history',
                      http_method='GET')
    def show_game_history(self, request):
        """Show current game state"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_historyform()
        else:
            endpoints.NotFoundException('Game not found. Enter valid key')

    @endpoints.method(request_message=USER_GAMES_REQUEST,
                      response_message=ShowGamesForms,
                      path='usergames',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Show all active games for a user"""
        result = ShowGamesForms()
        user = User.query(User.name == request.user_name).get().key

        games = Game.query(Game.userX == user, Game.game_ended == False)
        result.items = [self._copyToShowGamesForm(game, "X") for game in games]

        games = Game.query(Game.userO == user, Game.game_ended == False)
        result.items.extend(
            [self._copyToShowGamesForm(game, "O") for game in games])

        return result

    def _copyToShowGamesForm(self, game, symbol):
        """Copy data into ShowGamesForm"""

        if symbol == 'X':
            opponent = game.userO.get().name
        else:
            opponent = game.userX.get().name
        f = ShowGamesForm()
        f.symbol = symbol
        f.opponent = opponent
        f.urlsafekey = game.key.urlsafe()
        return f

    @endpoints.method(request_message=SHOW_GAME_REQUEST,
                      response_message=StringMessage,
                      path='cancelgame/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='POST')
    def cancel_game(self, request):
        """Cancel a game and remove from database"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            endpoints.NotFoundException('Game not found. Enter valid key')
        if game.game_ended:
            raise endpoints.ForbiddenException('Game has already ended')
        game.delete_game()
        return StringMessage(message="Game deleted !")

    @endpoints.method(request_message=USER_GAMES_REQUEST,
                      response_message=RankingForm,
                      path='userranking',
                      name='user_ranking',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Get a player's win loss ratio"""
        user = User.query(User.name == request.name).get()
        if not user:
            raise NotFoundException('User not found')
        games_lost = (user.games_completed-user.games_won-user.games_drawn)
        win_loss_ratio = user.games_won/games_lost
        return RankingForm(user_name=user.name, win_loss_ratio=win_loss_ratio)

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='makemove/{urlsafe_game_key}',
                      name='make_move',
                      http_method='POST')
    def make_move(self, request):
        """Validates a move, records it and moves the game forward"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            endpoints.NotFoundException('Game not found. Enter valid key')
        if game.game_ended:
            raise endpoints.ForbiddenException('Game has already ended')
        if game.next_turn.get().name != request.user:
            raise endpoints.UnauthorizedException("It is {}'s turn".format(
                            game.next_turn.get().name))
        if request.row not in range(3):
            raise endpoints.ForbiddenException('Row must be between 0 and 2')
        if request.col not in range(3):
            raise endpoints.ForbiddenException('Col must be between 0 and 2')
        if not game.validate_move(request.row, request.col):
            raise endpoints.ForbiddenException('That cell is not empty')
        if game.next_turn == game.userX:
            symbol = "X"
        else:
            symbol = "O"

        game = game.record_move(request.row, request.col, symbol)
        game.put()

        email_to = game.next_turn.get().email
        if game.check_winner():
            taskqueue.add(url='/SendMoveNotification',
                          params={'to': email_to, 'state': 'win',
                                  'opponent': game.winner.get().name})
            return game.to_form('Game over, {} wins !'.format(
                                        game.winner.get().name))

        elif game.check_draw():
            taskqueue.add(url='/SendMoveNotification',
                          params={'to': email_to, 'state': 'draw'})
            return game.to_form('It is a Draw ! Well Played both')

        else:
            taskqueue.add(url='/SendMoveNotification',
                          params={'to': email_to, 'state': ''})
            return game.to_form('Nice move ! {} to play next'.format(
                                    game.next_turn.get().name))


app = endpoints.api_server([TicTacToeApi])
