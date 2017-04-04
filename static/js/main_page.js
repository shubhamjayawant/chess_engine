var loadscreen = document.getElementById('myloadscreen');
var stopflag = false;
$(document).ready(function(){
    $('#tstBtn').click(function(){window.location.href = "testing_page.html";});
    $('#trnBtn').click(function(){
    	startTraining();
    	myPeriodicMethod();
    });
    $('#closeBtn').click(function(){stopflag = true; stopTraining();});
});

function startTraining(){
	$.ajax({
        type: "POST",
        url: "/start_training",
        success: trainingSuccess
    });
}

function stopTraining(){
    $.ajax({
        type: "POST",
        url: "/stop_training",
        success: stoppingSuccess
    });
}

function stoppingSuccess(response){
    console.log(response)
}


function trainingSuccess(response){
	console.log(response)
}

function myPeriodicMethod() {
  $.ajax({
  	type: 'POST',
    url: '/get_completion_status', 
    success: updateStatus
  });
}

function updateStatus(response) {
	$('#completionStatus').text(response);
	if ((response.indexOf('100') == -1) && stopflag == false){
		setTimeout(myPeriodicMethod, 3000);
	}
	else{
		setTimeout(function(){loadscreen.style.display = "none";alert(getDate())}, 1000);
	}
}

function getDate(){

    var currentdate = new Date(); 
    var datetime = "Training completed on: " + currentdate.getDate() + "/"
                    + (currentdate.getMonth()+1)  + "/" 
                    + currentdate.getFullYear() + " @ "  
                    + currentdate.getHours() + ":"  
                    + currentdate.getMinutes() + ":" 
                    + currentdate.getSeconds();

    return datetime

}

