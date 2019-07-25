"""

This is the server end of the chess engine.

"""

from flask import Flask, request, render_template
from chess import Move
from multiprocessing import Pool
import copy, re, os, chess, chess.pgn, json, random, pickle, os.path

app = Flask(__name__)
board, whose_playing, white_castle_status, black_castle_status = None, None, None, None
weights = []
current_board_features = []
games = []

# These variables can be altered in order to boost up or slow down the training cycle
game_pointer = 0
training_completion = 0
eta = 0.001
mobility_threshold = 0.6
number_of_iterations = 2
finished_iterations = 0

# This function loads the homepage
@app.route("/")
def index():
    return render_template('main_page.html')

# This function is called by the client to start a new training cycle
@app.route("/start_training", methods=['POST'])
def start_training():

    new_training()
    return 'Training has been started'

# This function initializes variables to a start new training cycle. It makes sure that training happens in
# the background as an async process
def new_training():

    global board, whose_playing, weights, current_board_features, training_completion,white_castle_status, black_castle_status
    load_games()
    initialize_weights_and_features()

    for i in range(0,number_of_iterations):

        for index,game in enumerate(games):

            pool = Pool(processes=1)
            board = chess.Board()
            whose_playing = chess.WHITE

            data = [game,board,whose_playing,weights,current_board_features, white_castle_status, black_castle_status]
            result = pool.apply_async(async_training, args=(data,), callback=get_updated_values)
            pool.close()
            pool.join()

    f = open('store.pckl', 'wb')
    pickle.dump(weights, f)
    f.close()

# This function loads chess games to be used for training from the memory
def load_games():

    global games

    for filename in os.listdir('data/'):
        if filename.endswith(".pgn"): 
            pgn = open('data/'+filename)
            first_game = chess.pgn.read_game(pgn)
            pgn.close()

            node = first_game
            game = []
            while not node.is_end():
                next_node = node.variation(0)
                game.append(node.board().san(next_node.move))
                node = next_node

            games.append(game)

# This function is used to get the percentage of games which have been referred in current iteration.
def get_updated_values(resultant_data):

    global games, game_pointer, training_completion, weights, current_board_features, white_castle_status, black_castle_status
    weights = resultant_data[0]
    current_board_features = resultant_data[1]
    white_castle_status = resultant_data[2]
    black_castle_status = resultant_data[3]

    game_pointer = game_pointer + 1
    training_completion = (game_pointer * 100)/len(games)

# This function carries out training over given parameters in the background
def async_training(params):

    global board, whose_playing, weights, current_board_features,white_castle_status, black_castle_status

    game = params[0]
    board = params[1]
    whose_playing = params[2]
    weights = params[3]
    current_board_features = params[4]
    white_castle_status = params[5]
    black_castle_status = params[6]

    for expected_move in game:

        get_current_board_features()
        actual_move = get_move_to_be_played(board,whose_playing)
        update_weights(expected_move,board.san(Move.from_uci(str(actual_move))))
        board.push_san(expected_move)

        if whose_playing == chess.WHITE:
            whose_playing = chess.BLACK
        else:
            whose_playing = chess.WHITE

    return [weights,current_board_features, white_castle_status, black_castle_status]

# This function returns how much training has been completed
@app.route("/get_completion_status", methods=['POST'])
def get_completion_status():

    global training_completion
    return str(int(training_completion/number_of_iterations))+'% finished'

# This function is called by the client side to stop on-going training cycle
@app.route("/stop_training", methods=['POST'])
def stop_training():

    global weights
    f = open('store.pckl', 'wb')
    pickle.dump(weights, f)
    f.close()

    return 'Training has been stopped successfully'

# This function initializes a new game of chess and loads the weights in memory.
@app.route("/testing_page.html")
def start_testing():

    global board, whose_playing
    board = chess.Board()
    whose_playing = chess.WHITE
    load_weights()
    return render_template('testing_page.html')

# This function loads weights from the memory
def load_weights():
    global weights

    f = open('store.pckl', 'rb')
    weights = pickle.load(f)
    f.close()

# This function is called by the client to send a user played move to the chess engine. This function returns 
# the move to be played by the chess engine to the client.
@app.route('/send_move', methods=['POST'])
def send_move():
    global board,whose_playing

    if len(re.findall('\\bO-O-O\\b', str(request.form['move']))) != 0:

        if whose_playing == chess.WHITE:
            white_castle_status = 'long_castle'
        if whose_playing == chess.BLACK:
            black_castle_status = 'long_castle'
    
    if len(re.findall('\\bO-O\\b', str(request.form['move']))) != 0 and len(re.findall('\\bO-O-O\\b', str(request.form['move']))) == 0:

        if whose_playing == chess.WHITE:
            white_castle_status = 'short_castle'
        if whose_playing == chess.BLACK:
            black_castle_status = 'short_castle'

    board.push_san(str(request.form['move']))

    print(board)
    print('----------------------------------------------')

    final_move = get_move_to_be_played(board,whose_playing)

    final_move = board.san(Move.from_uci(str(final_move)))

    board.push_san(final_move)
    
    print(board)

    if whose_playing == chess.WHITE:
        whose_playing = chess.BLACK
    else:
        whose_playing = chess.WHITE

    return str(board.fen())

# This function is called by the client to force the chess engine to make a move on current chess board
@app.route("/force_play", methods=['POST'])
def force_play():

    global board,whose_playing

    final_move = get_move_to_be_played(board,whose_playing)

    final_move = board.san(Move.from_uci(str(final_move)))

    board.push_san(final_move)
    
    print (board)

    if whose_playing == chess.WHITE:
        whose_playing = chess.BLACK
    else:
        whose_playing = chess.WHITE

    return str(board.fen())

#-------------------------------ML calculations--------------------------------#

# This function initializes the values of all the weights and board features to random values and 0 respectively
def initialize_weights_and_features():

    global weights,current_board_features
    
    for i in range(0,18):
        weights.append(random.uniform(0.0, 1.0))
        current_board_features.append(0)

#This function calculates the board features of current board position
def get_current_board_features():

    global current_board_features, board, whose_playing

    current_board_features[0] = (will_it_cause_check(board))
    current_board_features[1] = (will_it_cause_checkmate(board))
    current_board_features[2] = (will_the_king_be_safe(board,whose_playing))
    current_board_features[3] = (will_the_castle_be_safe(board,whose_playing))
    current_board_features[4] = (is_piece_free_to_move(board,whose_playing,chess.ROOK,14))
    current_board_features[5] = (is_piece_free_to_move(board,whose_playing,chess.KNIGHT,8))
    current_board_features[6] = (is_piece_free_to_move(board,whose_playing,chess.BISHOP,13))
    current_board_features[7] = (is_piece_free_to_move(board,whose_playing,chess.QUEEN,27))
    current_board_features[8] = (is_everything_safe(board,whose_playing,chess.PAWN))
    current_board_features[9] = (is_everything_safe(board,whose_playing,chess.ROOK))
    current_board_features[10] = (is_everything_safe(board,whose_playing,chess.KNIGHT))
    current_board_features[11] = (is_everything_safe(board,whose_playing,chess.BISHOP))
    current_board_features[12] = (is_everything_safe(board,whose_playing,chess.QUEEN))
    current_board_features[13] = (can_opps_unsupported_piece_be_killed(board,whose_playing,chess.PAWN))
    current_board_features[14] = (can_opps_unsupported_piece_be_killed(board,whose_playing,chess.ROOK))
    current_board_features[15] = (can_opps_unsupported_piece_be_killed(board,whose_playing,chess.KNIGHT))
    current_board_features[16] = (can_opps_unsupported_piece_be_killed(board,whose_playing,chess.BISHOP))
    current_board_features[17] = (can_opps_unsupported_piece_be_killed(board,whose_playing,chess.QUEEN))

def update_weights(expected_move, actual_move):

    global weights, eta, current_board_features


    expected_target_value = get_target_value(expected_move,board,whose_playing)
    actual_target_value = get_target_value(actual_move,board,whose_playing)

    for i,j in enumerate(weights):

        weights[i] = weights[i] + eta * (expected_target_value - actual_target_value) * current_board_features[i]

# This function calculates target values for all legal moves and then returns the move with highest target value
def get_move_to_be_played(board, whose_playing):

    moves_and_target_values = {}

    all_legal_moves = board.legal_moves

    for legal_move in all_legal_moves:

        moves_and_target_values[legal_move] = get_target_value(board.san(Move.from_uci(str(legal_move))),board,whose_playing)

    return max(moves_and_target_values, key=lambda i: moves_and_target_values[i])

# This function is used to calculate the target value of a given move
def get_target_value(move,board,whose_playing):

    temp_board = copy.deepcopy(board)
    temp_board.push_san(move)

    board_features = []
    board_features.append(will_it_cause_check(temp_board))
    board_features.append(will_it_cause_checkmate(temp_board))
    board_features.append(will_the_king_be_safe(temp_board,whose_playing))
    board_features.append(will_the_castle_be_safe(temp_board,whose_playing))
    board_features.append(is_piece_free_to_move(temp_board,whose_playing,chess.ROOK,14))
    board_features.append(is_piece_free_to_move(temp_board,whose_playing,chess.KNIGHT,8))
    board_features.append(is_piece_free_to_move(temp_board,whose_playing,chess.BISHOP,13))
    board_features.append(is_piece_free_to_move(temp_board,whose_playing,chess.QUEEN,27))
    board_features.append(is_everything_safe(temp_board,whose_playing,chess.PAWN))
    board_features.append(is_everything_safe(temp_board,whose_playing,chess.ROOK))
    board_features.append(is_everything_safe(temp_board,whose_playing,chess.KNIGHT))
    board_features.append(is_everything_safe(temp_board,whose_playing,chess.BISHOP))
    board_features.append(is_everything_safe(temp_board,whose_playing,chess.QUEEN))
    board_features.append(can_opps_unsupported_piece_be_killed(temp_board,whose_playing,chess.PAWN))
    board_features.append(can_opps_unsupported_piece_be_killed(temp_board,whose_playing,chess.ROOK))
    board_features.append(can_opps_unsupported_piece_be_killed(temp_board,whose_playing,chess.KNIGHT))
    board_features.append(can_opps_unsupported_piece_be_killed(temp_board,whose_playing,chess.BISHOP))
    board_features.append(can_opps_unsupported_piece_be_killed(temp_board,whose_playing,chess.QUEEN))

    global weights
    target_value = 0.0

    for i in range(0,len(board_features)):

        target_value = target_value + (board_features[i] * weights[i])

    return target_value

#----------------------------------------------------------------------------------#

#-------------------------------Board features calculation------------------------#

def will_it_cause_check(temp_board):

    if temp_board.is_check():
        return 1
    return 0

def will_it_cause_checkmate(temp_board):

    if temp_board.is_checkmate():
        return 10
    return 0

"""
This function decides whether the king is safe or not given the color of king and board position.

It checks for all the squares around the given king, if more than 3 squares adjacent to king's square are attacked
by the opposition, it returns 0 otherwise it returns 5.

"""
def will_the_king_be_safe(temp_board,whose_playing):

    def get_squares_to_consider(board,kings_position,whose_playing):

        to_return = []

        if (kings_position + 8) < 64:

            to_return.append(kings_position + 8)

            if (kings_position % 8) != 7:

                to_return.append(kings_position + 1)
                to_return.append(kings_position + 9)

            if (kings_position % 8) != 0:

                to_return.append(kings_position - 1)
                to_return.append(kings_position + 7)

        if (kings_position - 8) > 0:

            to_return.append(kings_position - 8)

            if (kings_position % 8) != 7:

                if (kings_position + 1) not in to_return:
                    
                    to_return.append(kings_position + 1)

                to_return.append(kings_position - 7)

            if (kings_position % 8) != 0:   
            
                if (kings_position - 1) not in to_return:
                    
                    to_return.append(kings_position - 1)

                to_return.append(kings_position - 9)         

        return to_return

    kings_position = [a for a in temp_board.pieces(chess.KING,whose_playing)][0]
    squares_to_consider = get_squares_to_consider(temp_board,kings_position,whose_playing)

    opposition_color = None
        
    if whose_playing == chess.WHITE:
        opposition_color = chess.BLACK
    
    else:
        opposition_color = chess.WHITE

    attack_count = 0

    for square in squares_to_consider:

        if temp_board.is_attacked_by(opposition_color,square):

            attack_count = attack_count + 1

    if attack_count > 3:
        return 0

    return 5

"""

Function which decides whether the castle of the given color is safe or not.

It considers only a quadrant of a chessboard for carrying out its operation. The selection of the quadrant
depends upon the color who is playing and the side on which the castle has been made. If number of attacked 
squares by the opposition are more than the safety_threshold then this function returns 0, otherwise it returns 5

"""

def will_the_castle_be_safe(temp_board,whose_playing):

    def has_castled(whose_playing):

        global white_castle_status, black_castle_status

        if whose_playing == chess.WHITE and white_castle_status is not None:
            return True

        elif whose_playing == chess.BLACK and black_castle_status is not None:
            return True

        return False

    def is_castle_safe(whose_playing,board):

        squares_to_consider = []
        safety_threshold = 4
        
        if whose_playing == chess.WHITE:

            if white_castle_status == 'long_castle':
                squares_to_consider = chess.SQUARES[0:4] + chess.SQUARES[8:12] + chess.SQUARES[16:20] + chess.SQUARES[24:28]

            else:
                squares_to_consider = chess.SQUARES[4:8] + chess.SQUARES[12:16] + chess.SQUARES[20:24] + chess.SQUARES[28:32]

            under_attack_count = 0
            for square in squares_to_consider:
                if board.is_attacked_by(chess.BLACK,square):
                    under_attack_count = under_attack_count + 1
                
                if under_attack_count > safety_threshold:
                    return False

            return True

        else:

            if black_castle_status == 'long_castle':
                squares_to_consider = chess.SQUARES[32:36] + chess.SQUARES[40:44] + chess.SQUARES[48:52] + chess.SQUARES[56:60]

            else:
                squares_to_consider = chess.SQUARES[36:40] + chess.SQUARES[44:48] + chess.SQUARES[52:56] + chess.SQUARES[60:64]

            under_attack_count = 0
            for square in squares_to_consider:
                if board.is_attacked_by(chess.WHITE,square):
                    under_attack_count = under_attack_count + 1
                
                if under_attack_count > safety_threshold:
                    return False

            return True

    if has_castled(whose_playing) and is_castle_safe(whose_playing,temp_board):
        return 5
    return 0

# This function returns the positions of the pieces given piece type, the color to consider and the board position
def get_piece_position(board,whose_playing,piece):

    return [square for square in board.pieces(piece,whose_playing)]

# This function calculates the mobility of any given piece on a given chess board
def get_mobility(board,piece_position):

    return len([temp for temp in board.attacks(piece_position)]) * 1.0

""" 

This function determines whether a piece is free to move or not
It calculates the mobility of the piece and then compares it with the threshold value of that piece.

"""
def is_piece_free_to_move(temp_board,whose_playing,piece,threshold):

    temp_mobility = 0.0
    positions = get_piece_position(temp_board,whose_playing,piece)

    for piece_position in positions:
        temp_mobility = temp_mobility + float(get_mobility(temp_board,piece_position)/threshold)

    if len(positions) != 0 and (temp_mobility/len(positions)) < threshold:
        return 0

    return 1

"""

This function checks whether all the pieces of any given color on a given board are attacked by the opposition 
or not. If certain unsupported piece is under attack of the opposition, it returns 0. Else, it returns 8.

"""
def is_everything_safe(temp_board,whose_playing,piece):

    def is_unsupported(board,piece_position,whose_playing):

        if board.is_attacked_by(whose_playing,piece_position) is False:
            return True

        return False

    def is_under_attack(board,piece_position,whose_playing):

        opposition_color = None
        
        if whose_playing == chess.WHITE:
            opposition_color = chess.BLACK
        
        else:
            opposition_color = chess.WHITE

        if board.is_attacked_by(opposition_color,piece_position):
            return True

        return False

    positions = get_piece_position(temp_board,whose_playing,piece)

    for piece_position in positions:

        if is_unsupported(temp_board,piece_position,whose_playing) and is_under_attack(temp_board,piece_position,whose_playing):
            return 0

    return 8

"""

This function checks whether opposition's any piece is unsupported and can be captured by any of 
the given color's pieces. If such piece is found, it returns 5. Else, it returns 0.

"""
def can_opps_unsupported_piece_be_killed(temp_board,whose_playing,piece):

    def is_unsupported(board,piece_position,opposition_color):

        if board.is_attacked_by(opposition_color,piece_position) is False:
            
            return True

        return False

    def can_be_attacked(board,position,whose_playing):

        if board.is_attacked_by(whose_playing,piece_position):
            
            return True

        return False

    opposition_color = None
        
    if whose_playing == chess.WHITE:
        opposition_color = chess.BLACK
    
    else:
        opposition_color = chess.WHITE

    positions = get_piece_position(temp_board,opposition_color,piece)

    for piece_position in positions:

        if is_unsupported(temp_board,piece_position,opposition_color) and can_be_attacked(temp_board,piece_position,whose_playing):

            return 5

    return 0

#---------------------------------------------------------------------------------#
 
if __name__ == "__main__":
    app.run(threaded=True)