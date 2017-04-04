var board,
  game = new Chess()

  $(document).ready(function(){
    $('#newGameBtn').click(function(){location.reload()});
    $('#forcePlayBtn').click(function(){
        $.ajax({
          type: "POST",
          url: "/force_play",
          success: make_move
      });
    });
});

var onDragStart = function(source, piece, position, orientation) {
  if (game.game_over() === true ||
      (game.turn() === 'w' && piece.search(/^b/) !== -1) ||
      (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
    return false;
  }
};

var onDrop = function(source, target) {

  var move = game.move({
    from: source,
    to: target,
    promotion: 'q'
  });

  if (move === null) return 'snapback';

  temp = game.pgn();
  to_send = temp.split(" ");
  if (game.in_checkmate() === false) {
    send_move_to_engine(to_send[to_send.length - 1]);
  }
};

function send_move_to_engine(input) {
  $.ajax({
        type: "POST",
        url: "/send_move",
        data: { move: input },
        success: on_success
    });
}

function on_success(response) {
    board.position(response,true);
    game.load(response);
}

var cfg = {
  snapbackSpeed: 550,
  appearSpeed: 550,
  draggable: true,
  position: 'start',
  onDragStart: onDragStart,
  onDrop: onDrop,
  pieceTheme: 'http://www.willangles.com/projects/chessboard/img/chesspieces/wikipedia/{piece}.png'
};

board = new ChessBoard('board', cfg);
$(window).resize(board.resize);
$('#flipBoardBtn').on('click', board.flip);