"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    games_in_progress = ndb.IntegerProperty(default=0)
    games_completed = ndb.IntegerProperty(default=0)
    games_won = ndb.IntegerProperty(default=0)
    games_drawn = ndb.IntegerProperty(default=0)

    def to_form(self):
        return UserForm(name=self.name, email=self.email,
                        games_in_progress=self.games_in_progress,
                        games_completed=self.games_completed,
                        games_won=self.games_won,
                        games_drawn=self.games_drawn)


class TicTacToe(ndb.Model):
    """Array board for tic tac toe"""
    row1 = ndb.StringProperty()
    row2 = ndb.StringProperty()
    row3 = ndb.StringProperty()


class GameHistory(ndb.Model):
    """Structure for recording game history"""
    sequence = ndb.IntegerProperty()
    user = ndb.KeyProperty(kind=User)
    move = ndb.StringProperty()
    result = ndb.StringProperty()


class Game(ndb.Model):
    """Game details"""
    userX = ndb.KeyProperty(required=True, kind=User)
    userO = ndb.KeyProperty(required=True, kind=User)
    game_ended = ndb.BooleanProperty(required=True, default=False)
    draw = ndb.BooleanProperty(required=True, default=False)
    turns_played = ndb.IntegerProperty(default=0)
    next_turn = ndb.KeyProperty(kind=User)
    winner = ndb.KeyProperty(kind=User)
    game_state = ndb.StructuredProperty(TicTacToe)
    debug = ndb.StringProperty()
    history = ndb.StructuredProperty(GameHistory, repeated=True)

    @classmethod
    def new_game(cls, userX, userO):
        """Creates a new empty game between 2 users

        Args:
            user keys for players

        Returns:
            Object of class Game

        """
        board = TicTacToe(row1='___', row2='___', row3='___')
        game = Game(userX=userX, userO=userO, game_ended=False,
                    game_state=board, next_turn=userX)
        game.put()
        userobjX = userX.get()
        userobjO = userO.get()
        userobjX.games_in_progress += 1
        userobjO.games_in_progress += 1
        userobjX.put()
        userobjO.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game

        Args:
            Optional String message

        Returns:
            Game details in the GameForm format

        """
        form = GameForm()
        form.userX = self.userX.get().name
        form.userO = self.userO.get().name
        form.row1 = self.game_state.row1
        form.row2 = self.game_state.row2
        form.row3 = self.game_state.row3
        form.turns_played = self.turns_played
        form.next_turn = self.next_turn.get().name
        form.game_ended = self.game_ended
        form.urlsafekey = self.key.urlsafe()
        form.message = message
        form.debug = self.debug
        form.draw = self.draw
        return form

    def to_historyform(self):
        """Returns a GameHistoryForm representation of the Game history"""
        ret = GameHistoryForms()
        for history in self.history:
            form = GameHistoryForm()
            form.sequence = history.sequence
            form.user = history.user.get().name
            form.move = history.move
            form.result = history.result
            ret.items.append(form)
        return ret

    def game_over(self, winner, draw):
        """End the game, record the winner or draw for history
        and update user statistics in User objects

        Args:
            winner: user key for winner of the game
            draw: boolean flag if game is a draw

        """
        if not winner and not draw:
            raise ValueError("No winner specified")
        self.game_ended = True
        userX = self.userX.get()
        userO = self.userO.get()
        if not draw:
            self.winner = winner
            winner.get().games_won += 1
            self.history[len(self.history)-1].result = '%s won !' % winner.get().name
        else:
            self.draw = True
            userX.games_drawn += 1
            userO.games_drawn += 1
            self.history[len(self.history)-1].result = 'Game drawn'
        userX.games_in_progress -= 1
        userO.games_in_progress -= 1
        userX.games_completed += 1
        userO.games_completed += 1
        userX.put()
        userO.put()
        self.put()

    def validate_move(self, row, col):
        """Check if move is on empty space

        Returns:
            Boolean flag if move is valid

        """
        if row == 0:
            selectedRow = self.game_state.row1
        if row == 1:
            selectedRow = self.game_state.row2
        if row == 2:
            selectedRow = self.game_state.row3
        if selectedRow[col] == '_':
            return True
        return False

    def record_move(self, row, col, symbol):
        """Record the move in the game state and update next turn

        Args:
            row, column and symbol of the move

        """
        # Initialize history for the move
        history = GameHistory()

        # Get the row based on input
        if row == 0:
            selectedRow = self.game_state.row1
        if row == 1:
            selectedRow = self.game_state.row2
        if row == 2:
            selectedRow = self.game_state.row3

        # Representation of the selected row after making the move    
        newRow = ''
        for i in range(3):
            if i == col:
                newRow += symbol
            else:
                newRow += selectedRow[i]
        self.debug = newRow

        # Record the new representation of the row
        if row == 0:
            self.game_state.row1 = newRow
        if row == 1:
            self.game_state.row2 = newRow
        if row == 2:
            self.game_state.row3 = newRow

        # Update history
        if symbol == "X":
            self.next_turn = self.userO
            history.user = self.userX
        else:
            self.next_turn = self.userX
            history.user = self.userO
        # Record game history
        self.turns_played += 1
        history.sequence = self.turns_played
        history.move = (','.join([str(row), str(col)]))
        self.history.append(history)

        self.put()
        return self

    def check_winner(self):
        """Check if the game has been won

        Returns:
            Boolean flag if game has ended in a win

        """
        game_arrayX = self.generateArray("X")
        game_arrayO = self.generateArray("O")
        win = False
        winner = ''
        """Check row totals for userX"""
        for row in range(3):
            if sum(game_arrayX[row][col] for col in range(3)) == 3:
                win = True
                winner = self.userX
        """Check column totals for userX"""
        for col in range(3):
            if sum(game_arrayX[row][col] for row in range(3)) == 3:
                win = True
                winner = self.userX
        """Check diagonal totals for userX"""
        if sum(game_arrayX[row][row] for row in range(3)) == 3:
            win = True
            winner = self.userX
        if sum(game_arrayX[row][2-row] for row in range(3)) == 3:
            win = True
            winner = self.userX
        """Check row totals for userO"""
        for row in range(3):
            if sum(game_arrayO[row][col] for col in range(3)) == 3:
                win = True
                winner = self.userO
        """Check column totals for userO"""
        for col in range(3):
            if sum(game_arrayO[row][col] for row in range(3)) == 3:
                win = True
                winner = self.userO
        """Check diagonal totals for userO"""
        if sum(game_arrayO[row][row] for row in range(3)) == 3:
            win = True
            winner = self.userO
        if sum(game_arrayO[row][2-row] for row in range(3)) == 3:
            win = True
            winner = self.userO

        if win:
            self.game_over(winner, False)

        return win

    def check_draw(self):
        """Check if the game is a draw

        Returns:
            Boolean flag if game has ended in a draw

        """
        draw = True
        for col in range(3):
            if self.game_state.row1[col] == '_':
                draw = False
                break
            if self.game_state.row2[col] == '_':
                draw = False
                break
            if self.game_state.row3[col] == '_':
                draw = False
                break
        if draw:
            self.game_over(None, draw)
        return draw

    def delete_game(self):
        """Delete game and remove it from user stats

        Raises:
            InternalServerErrorException: if any error occured in deletion

        """
        try:
            userX = self.userX.get()
            userX.games_in_progress -= 1
            userO = self.userO.get()
            userO.games_in_progress -= 1
            userX.put()
            userO.put()
            self.key.delete()
        except:
            raise endpoints.InternalServerErrorException('Could not delete')

    def generateArray(self, symbol):
        """Mask a symbol with 1's and generate the board as matrix

        Args:
            symbox 'X' or 'O'

        Returns:
            array where symbol has been replaced by integer 1

        """
        arr = [[0 for x in range(3)] for x in range(3)]
        for col in range(3):
            arr[0][col] = self.mask(self.game_state.row1[col], symbol)
            arr[1][col] = self.mask(self.game_state.row2[col], symbol)
            arr[2][col] = self.mask(self.game_state.row3[col], symbol)
        return arr

    @staticmethod
    def mask(value, symbol):
        """Replace symbol with 1"""
        if value == symbol:
            return 1
        return 0


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    userX = messages.StringField(1, required=True)
    userO = messages.StringField(2, required=True)
    game_ended = messages.BooleanField(3, required=True)
    row1 = messages.StringField(4)
    row2 = messages.StringField(5)
    row3 = messages.StringField(6)
    next_turn = messages.StringField(7)
    urlsafekey = messages.StringField(8, required=True)
    message = messages.StringField(9)
    draw = messages.BooleanField(10)
    debug = messages.StringField(11)
    turns_played = messages.IntegerField(12)


class NewGameForm(messages.Message):
    """Form for creating a new game """
    userX = messages.StringField(1, required=True)
    userO = messages.StringField(2, required=True)


class ShowGamesForm(messages.Message):
    """Outbound form for all active user games """
    symbol = messages.StringField(1)
    opponent = messages.StringField(2)
    urlsafekey = messages.StringField(3)


class ShowGamesForms(messages.Message):
    items = messages.MessageField(ShowGamesForm, 1, repeated=True)


class MakeMoveForm(messages.Message):
    """Outbound form for making a game move"""
    user = messages.StringField(1, required=True)
    row = messages.IntegerField(2, required=True)
    col = messages.IntegerField(3, required=True)


class UserForm(messages.Message):
    """Outbound form for user details"""
    name = messages.StringField(1, required=True)
    email = messages.StringField(2)
    games_in_progress = messages.IntegerField(3)
    games_completed = messages.IntegerField(4)
    games_won = messages.IntegerField(5)
    games_drawn = messages.IntegerField(6)


class UserForms(messages.Message):
    items = messages.MessageField(UserForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)


class RankingForm(messages.Message):
    """Outbound form for showing single user rankigns"""
    rank = messages.IntegerField(1)
    user_name = messages.StringField(2)
    win_loss_ratio = messages.FloatField(3)

class RankingForms(messages.Message):
    """Outbound form for multiple user rankings"""
    items = messages.MessageField(RankingForm,1,repeated=True)


class GameHistoryForm(messages.Message):
    """Outbound form for line of game history"""
    sequence = messages.IntegerField(1)
    user = messages.StringField(2)
    move = messages.StringField(3)
    result = messages.StringField(4)


class GameHistoryForms(messages.Message):
    """Outbound form for all game history"""
    items = messages.MessageField(GameHistoryForm, 1, repeated=True)
