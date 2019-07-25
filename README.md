# Chess Engine

A trainable chess engine with an integrated GUI which uses linear regression to make decisions.

## How does it work?
1. The chess engine is trained using the [games](/data) played by renowned players.
2. The engine makes use of a feature computer which returns a vector of feature values given a board state.
3. Upon receiving this vector, it is matched with the knowledge base.
4. The ability to match board states is learned using linear regression.
5. After matching, the move to be played is determined from the board state closest to the current state.

## Usage:

1. Execute the python script [chess_engine.py](/chess_engine.py) 
2. Log on to `http://localhost:5000` in your browser. 
3. Select one of the following modes,
	1. Training mode:	Train your chess engine.
	2. Testing mode:	Play a game of chess against your chess engine. Theme of the chess pieces and style of board can be changed from the files [testing_page.html](/templates/testing_page.html) and [index.js](/static/js/index.js). 

## Screenshots:

 _Mode selection menu_
 ![Mode selection menu](https://github.com/shubhamjayawant/chess_engine/blob/master/screenshots/1.png)

 _Chess engine training in progress_
 ![Chess engine training in progress](https://github.com/shubhamjayawant/chess_engine/blob/master/screenshots/2.png)

 _Chess engine playing with white pieces_
 ![Chess engine playing with white pieces](https://github.com/shubhamjayawant/chess_engine/blob/master/screenshots/3.png)

 _Chess engine playing with black pieces_
 ![Chess engine playing with black pieces](https://github.com/shubhamjayawant/chess_engine/blob/master/screenshots/4.png)