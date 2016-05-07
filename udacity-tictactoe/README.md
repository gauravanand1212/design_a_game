#Full Stack Nanodegree Project 4 

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
1.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
1.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.
 
 
 
##Game Description:
TicTacToe is a 2 player game played on a 3x3 board. Each player chooses a symbol (X or O)
and enters it on a cell on the board. Players take turn to play their move. Any 
player with symbols that form a 3-in-a-row horizontally, vertically or diagonally
wins. If all 9 cells are filled and no one has the winning combination, the game 
is a draw.
The system keeps a track of wins, draws and total games played by a user. Players are
ranked based on their win-loss ratio, which is the ratio of games won and games lost 
(ignoring games drawn).
Each game can be retrieved or played by using the path parameter
`urlsafe_game_key`.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.


##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists.

 - **get_users**
    - Path: 'userstats'
    - Method: GET
    - Parameters: 
    - Returns: List of active users and their gaming statistics
    - Description: Gives a list of users in the system and their statistics
    on tic tac toe, including games played, won, drawn, in-progress

 - **create_new_game**
    - Path: 'newgame'
    - Method: POST
    - Parameters: userX, userO
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. userX and userO indicate user names
    for users with X and O symbols respectively. If user names do not exist in 
    the system, NotFoundException is raised.
     
 - **show_game**
    - Path: 'showgame/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.
    
 - **show_game_history**
    - Path: 'showgamehistory/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameHistoryForm with history of moves in the gae
    - Description: Returns the history of a game.

 - **get_user_games**
    - Path: 'usergames'
    - Method: GET
    - Parameters: user_name
    - Returns: ShowGamesForm with all active games with user
    - Description: Returns all games the user is a part of that have not ended

- **cancel_game**
    - Path: 'cancelgame/{urlsafe_game_key}'
    - Method: POST
    - Parameters: urlsafe_game_key
    - Returns: Message confirming deletion of game
    - Description: Deletes an active game. If game has already ended, raises
    ForbiddenException. If game does not exist, raises NotFoundException

- **user_ranking**
    - Path: 'userranking'
    - Method: GET
    - Parameters: user_name
    - Returns: UserRankingForm with user name and win loss ration
    - Description: Returns the win loss ration for a user. Win loss ratio
    is defined as total games won / total games lost. Draws do not count.

 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, row, col, user
    - Returns: GameForm with new game state.
    - Description: Accepts a row and col where the specified user wants to 
    make a move. If row/col are already filled, raises ForbiddenException.
    If wrong user tries to make a move, raises UnAuthorizedException. Once 
    move is made, checks with game has ended (win/draw) and sends email to 
    the other user accordingly
    
 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).


##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
 - **TicTacToe**
    - Game board. Used as a structured property in Game

- **GameHistory**
    - Records game history as a strucutred prooprty in Game
    
##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, users, game board).
 - **NewGameForm**
    - Used to create a new game (userX, userO)
 - **ShowGamesForm**
    - Used to show an active game for a user (symbol, opponent name)
 - **ShowGamesForms**
    - Multiple ShowGamesForm container.
 - **MakeMoveForm**
    - Inbound make move form (user, row, col).
 - **UserForm**
    - Outbound form for getting user details and stats
 - **UserForms**
    - Multiple UserForm container.
 - **StringMessage**
    - General purpose String container.
 - **RankingForm**
    - Form containing name, win-loss ratio and rank for a user
 - **RankingForm*s*
    - Multiple RankingForm container
 - **GameHistoryForm**
    - Used to show a historical move for a game (user,move,result)
 - **GameHistoryForms**
    - Multiple GameHistoryForm container.

