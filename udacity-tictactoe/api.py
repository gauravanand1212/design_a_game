# -*- coding: utf-8 -*-`
"""api.py - TiTacToe Game API
Contains the endpoint methods to access the game and make moves.
Messaging system allows users to keep track of the tic tac toe
board. """


import endpoints
from google.appengine.api import taskqueue
from protorpc import remote, messages

from models import User, Game
from models import UserForms, ShowGamesForm, ShowGamesForms
from models import GameForm, NewGameForm, MakeMoveForm, StringMessage
from models import RankingForm, RankingForms

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
        """Create a User. Requires a unique username

        Args: 
          CREATE_USER_REQUEST: user and email

        Returns:
          Confirmation message about creation of user in database

        Raises:
          ConflictException if a user with same name already exists

        """
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
        """Get a list of all users and their stats

        Returns:
          A list of all users in form UserForms

        """
        return UserForms(items=[user.to_form() for user in User.query()])

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='newgame',
                      name='create_new_game',
                      http_method='POST')
    def create_new_game(self, request):
        """Create a new tictactoe game between 2 players

        Args: 
          NEW_GAME_REQUEST: Details of new game in GameForm format

        Returns:
          New game in GameForm format along with Confirmation message

        Raises:
          NotFoundException: if either user specified in input GameForm
          is not found in user model

        """
        userX = User.query(User.name == request.userX)
        userO = User.query(User.name == request.userO)
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
        """Show current game state

        Args:
          SHOW_GAME_REQUEST: request containing urlsafekey of a game

        Returns:
          Existing game details in GameForm format

        Raises:
          NotFoundException: If no game found using the urlsafekey provided

        """
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
        """Show game history

        Args:
          SHOW_GAME_REQUEST: request containing urlsafekey of a game

        Returns:
          History of moves and results in a game in GameHistoryForms format

        Raises:
          NotFoundException: If no game found using the urlsafekey provided

        """
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
        """Show all active games for a user

        Args:
          USER_GAMES_REQUEST: name of the user

        Returns:
          symbol, opponent and urlsafekey for games the user is
          still an active participant wrapped in ShowGamesForms format

        """
        result = ShowGamesForms()
        user = User.query(User.name == request.user_name).get().key

        games = Game.query(Game.userX == user, Game.game_ended == False)
        result.items = [self._copyToShowGamesForm(game, "X") for game in games]

        games = Game.query(Game.userO == user, Game.game_ended == False)
        result.items.extend(
            [self._copyToShowGamesForm(game, "O") for game in games])

        return result

    def _copyToShowGamesForm(self, game, symbol):
        """Copy data into ShowGamesForm

        Args:
          game: object of class Game
          symbol: 'X' or 'O' depending on what player chose

        Returns:
          symbol, opponent and urlsafekey for game in ShowGamesForm format

        """

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
        """Cancel a game and remove from database

        Args:
          SHOW_GAME_REQUEST: urlsafekey for the game

        Returns:
          Confirmation message about successful game deletion

        Raises:
          NotFoundException: If no game matches the urlsafekey
          ForbiddenException: If the game provided is not active or 
          has already ended

        """
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            endpoints.NotFoundException('Game not found. Enter valid key')
        if game.game_ended:
            raise endpoints.ForbiddenException('Game has already ended')
        game.delete_game()
        return StringMessage(message="Game deleted !")

    @endpoints.method(response_message=RankingForms,
                      path='userranking',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Get player rankings by win loss ratios

        Returns:
          Sorted rankings of players ranked by decreasing win-loss
          ratio in RankingForms format

        Raises:
          NotFoundException: if no players exist in database

        """
        users = User.query().fetch()
        if not users:
            raise NotFoundException('No users not found')

        ranked_users = []
        for user in users:
          games_lost = (user.games_completed-user.games_won-user.games_drawn)
          # Avoid divide by zero error
          if games_lost == 0:
            win_loss_ratio = 1.0
          else:
            win_loss_ratio = float(user.games_won/games_lost)
          ranked_users.append([user.name,win_loss_ratio])
        ranked_users.sort(key= lambda ranking: ranking[1], reverse=True)

        """Copy to form """
        retForm = RankingForms()
        rank = 1
        for ranked_user in ranked_users:
          form = RankingForm()
          form.rank = rank
          form.user_name = ranked_user[0]
          form.win_loss_ratio = ranked_user[1]
          retForm.items.append(form)
          rank += 1
        return retForm


    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='makemove/{urlsafe_game_key}',
                      name='make_move',
                      http_method='POST')
    def make_move(self, request):
        """Validates a move, records it and moves the game forward. Also
        adds email alerts to taskqueue to inform next user of pending moves
        or game result

        Args:
          urlsafekey, row, col and player name making the move in the game

        Returns:
          Game details in GameForm format along with confirmation message
          about move being recorded

        Raises:
          NotFoundException: 
            If no game found using urlsafekey
          ForbiddenException: 
            Game has already ended
            Incorrect row or column value has been passed
            Invalid move as the cell has already been filled
          UnauthorizedException:
            Wrong player is trying to make a move

        """
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

        # Set up taskqueues to send notifications
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
